"""
text_to_sql.py  —  Natural Language → SQL
==========================================
Primary  : Groq API (llama-3.3-70b-versatile)
Fallback : Rule-based parser

Handles:
  • year / date      →  WHERE year = 1930 / BETWEEN 1990 AND 2000
  • rating numbers   →  WHERE rating > 8
  • genre LIKE       →  WHERE genre LIKE '%Drama%'
  • text LIKE        →  WHERE title LIKE '%godfather%'
  • aggregates       →  COUNT / AVG / MAX / MIN / SUM
  • ordering         →  ORDER BY rating DESC
  • limit            →  LIMIT 10
  • multi-table      →  uses all tables in schema
  • director / stars search via LIKE
"""

import os
import re
import logging

logger = logging.getLogger(__name__)


class TextToSQL:
    def __init__(self, anthropic_api_key=None):
        self.api_key = os.environ.get("GROQ_API_KEY") or anthropic_api_key
        self._client = None
        if self.api_key:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info("Groq API ready")
            except ImportError:
                logger.warning("groq not installed — rule-based only")

    def convert(self, question: str, schema: list, rag_context: str = "") -> dict:
        if self._client:
            r = self._groq(question, schema, rag_context)
            if r["success"]:
                return r
            logger.warning("Groq failed, falling back to rule-based")
        return self._rule(question, schema)

    # ── Groq API ───────────────────────────────────────────────
    def _groq(self, question, schema, rag_context: str = ""):
        schema_text = "\n".join(
            f"Table '{t['name']}' columns: " +
            ", ".join(f"{c['name']} ({c['type']})" for c in t["columns"])
            for t in schema
        )

        rag_block = ""
        if rag_context:
            rag_block = f"\nRELEVANT CONTEXT (schema facts + examples):\n{rag_context}\n"

        prompt = f"""You are an expert SQLite query generator. Your job is to convert natural language questions into valid SQLite SELECT statements.

DATABASE SCHEMA:
{schema_text}
{rag_block}
STRICT RULES:
1. Output ONLY the raw SQL SELECT statement — no markdown, no backticks, no explanation, no comments.
2. NEVER use DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, PRAGMA or any destructive statement.
3. Use EXACT column and table names from the schema above.
4. Wrap column or table names that contain spaces or special characters in double quotes.
5. For partial text matches, use LIKE with % wildcards (case-insensitive).
6. Always prefer specific columns over SELECT * when the question asks for specific info.
7. Use LIMIT 100 as default when no limit is specified and result could be large.
8. For aggregations (count, average, sum, max, min), use appropriate aliases.
9. For multi-table queries, use proper JOIN syntax with ON conditions.
10. If the question cannot be answered with the given schema, output exactly: CANNOT_GENERATE

Question: {question}
SQL:"""
        try:
            resp = self._client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a SQLite expert. Output only raw SQL, nothing else."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=300,
            )
            sql = resp.choices[0].message.content.strip()
            # Strip markdown fences if model adds them
            sql = re.sub(r"^```[a-zA-Z]*\n?", "", sql)
            sql = re.sub(r"```$", "", sql).strip()
            # Remove any trailing semicolon
            sql = sql.rstrip(";").strip()

            if "CANNOT_GENERATE" in sql or not sql.upper().startswith("SELECT"):
                return {"success": False}
            return {"success": True, "sql": sql, "source": "groq"}
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return {"success": False}

    # ── Rule-Based Engine ──────────────────────────────────────
    def _rule(self, question: str, schema: list) -> dict:
        if not schema:
            return {"success": False, "suggestions": ["Upload a dataset first"]}

        table   = schema[0]
        tname   = f'"{table["name"]}"'
        columns = table["columns"]
        q       = question.lower().strip()
        q       = re.sub(r"[?!.]", "", q)

        col_lookup = {c["name"].lower(): c for c in columns}

        # ── Aggregate intents ──
        agg = self._agg(q, columns, tname, col_lookup)
        if agg:
            return {"success": True, "sql": agg, "source": "rule_based"}

        # ── WHERE clauses ──
        where_parts = []
        where_parts += self._year_condition(q, col_lookup)
        where_parts += self._numeric_conditions(q, columns)
        where_parts += self._genre_condition(q, col_lookup)
        where_parts += self._text_conditions(q, columns)

        # Deduplicate
        where_parts = list(dict.fromkeys(where_parts))

        # ── SELECT cols ──
        select_cols = self._select_cols(q, columns)
        select_sql  = ", ".join(f'"{c}"' for c in select_cols) if select_cols else "*"

        # ── ORDER BY ──
        order_sql = self._order_by(q, columns)

        # ── LIMIT ──
        limit_sql = self._limit(q)

        # ── Assemble ──
        sql = f"SELECT {select_sql} FROM {tname}"
        if where_parts:
            sql += " WHERE " + " AND ".join(where_parts)
        if order_sql:
            sql += f" ORDER BY {order_sql}"
        if limit_sql:
            sql += f" LIMIT {limit_sql}"
        elif not where_parts and not order_sql:
            sql += " LIMIT 100"

        return {"success": True, "sql": sql, "source": "rule_based"}

    # ── Aggregate ──────────────────────────────────────────────
    def _agg(self, q, columns, tname, col_lookup):
        num_col = self._best_num_col(q, columns)

        if re.search(r"\b(how many|count|total number|number of)\b", q):
            where = self._conditions_str(q, columns, col_lookup)
            return f"SELECT COUNT(*) AS total FROM {tname}" + (f" WHERE {where}" if where else "")

        if re.search(r"\b(average|avg|mean)\b", q):
            col = num_col
            if col:
                where = self._conditions_str(q, columns, col_lookup)
                return f'SELECT AVG("{col}") AS avg_{col} FROM {tname}' + (f" WHERE {where}" if where else "")

        if re.search(r"\b(total gross|total earning|total revenue|sum of|total)\b", q):
            col = num_col
            if col:
                return f'SELECT SUM("{col}") AS total FROM {tname}'

        if re.search(r"\b(highest rated|best rated|top rated|most popular|best)\b", q):
            col = self._col_real_name(["rating", "score"], col_lookup) or num_col
            limit = self._limit(q) or "10"
            if col:
                return f'SELECT * FROM {tname} ORDER BY "{col}" DESC LIMIT {limit}'

        if re.search(r"\b(lowest rated|worst rated|least popular|worst)\b", q):
            col = self._col_real_name(["rating", "score"], col_lookup) or num_col
            limit = self._limit(q) or "10"
            if col:
                return f'SELECT * FROM {tname} ORDER BY "{col}" ASC LIMIT {limit}'

        if re.search(r"\b(max|maximum|highest|largest|biggest)\b", q):
            col = num_col
            if col:
                return f'SELECT MAX("{col}") AS max_{col} FROM {tname}'

        if re.search(r"\b(min|minimum|lowest|smallest)\b", q):
            col = num_col
            if col:
                return f'SELECT MIN("{col}") AS min_{col} FROM {tname}'

        return None

    def _conditions_str(self, q, columns, col_lookup):
        parts = []
        parts += self._year_condition(q, col_lookup)
        parts += self._numeric_conditions(q, columns)
        parts += self._genre_condition(q, col_lookup)
        parts += self._text_conditions(q, columns)
        return " AND ".join(dict.fromkeys(parts))

    # ── Year condition ─────────────────────────────────────────
    def _year_condition(self, q, col_lookup):
        year_col = self._col_real_name(["year", "release_year", "released"], col_lookup)
        if not year_col:
            return []

        m = re.search(r"\bbetween\s+((?:18|19|20)\d{2})\s+(?:and|to)\s+((?:18|19|20)\d{2})\b", q)
        if m:
            return [f'"{year_col}" BETWEEN {m.group(1)} AND {m.group(2)}']

        m = re.search(r"\bfrom\s+((?:18|19|20)\d{2})\s+to\s+((?:18|19|20)\d{2})\b", q)
        if m:
            return [f'"{year_col}" BETWEEN {m.group(1)} AND {m.group(2)}']

        m = re.search(r"\b(?:after|since|post)\s+((?:18|19|20)\d{2})\b", q)
        if m:
            return [f'"{year_col}" > {m.group(1)}']

        m = re.search(r"\b(?:before|prior to|until)\s+((?:18|19|20)\d{2})\b", q)
        if m:
            return [f'"{year_col}" < {m.group(1)}']

        m = re.search(r"\b(?:in|of|year|released in|from|made in)\s+((?:18|19|20)\d{2})\b", q)
        if m:
            return [f'"{year_col}" = {m.group(1)}']

        m = re.search(r"\b((?:18|19|20)\d{2})\b", q)
        if m:
            yr = int(m.group(1))
            if 1880 <= yr <= 2030:
                return [f'"{year_col}" = {yr}']

        return []

    # ── Numeric conditions ─────────────────────────────────────
    def _numeric_conditions(self, q, columns):
        parts = []
        num_cols = [c for c in columns if c.get("type") in ("INTEGER", "REAL", "NUMERIC")]

        for col in num_cols:
            name = col["name"]
            nl   = name.lower()
            if nl in ("year", "release_year", "released"):
                continue

            aliases   = self._col_aliases(nl)
            alias_pat = "|".join(re.escape(a) for a in aliases)

            m = re.search(
                rf"(?:{alias_pat})\s*(?:above|greater than|more than|over|>|higher than|at least|>=)\s*(\d+\.?\d*)", q)
            if not m:
                m = re.search(
                    rf"(?:above|greater than|more than|over|higher than|at least)\s+(\d+\.?\d*)\s+(?:\w+\s+)?(?:{alias_pat})", q)
            if m:
                parts.append(f'"{name}" > {m.group(1)}')
                continue

            m = re.search(
                rf"(?:{alias_pat})\s*(?:below|less than|under|<|lower than|at most|<=)\s*(\d+\.?\d*)", q)
            if not m:
                m = re.search(
                    rf"(?:below|less than|under|lower than|at most)\s+(\d+\.?\d*)\s+(?:\w+\s+)?(?:{alias_pat})", q)
            if m:
                parts.append(f'"{name}" < {m.group(1)}')
                continue

            m = re.search(
                rf"(?:{alias_pat})\s*(?:between)\s*(\d+\.?\d*)\s*(?:and|to)\s*(\d+\.?\d*)", q)
            if m:
                parts.append(f'"{name}" BETWEEN {m.group(1)} AND {m.group(2)}')
                continue

            m = re.search(rf"(?:{alias_pat})\s*(?:is|=|equals?|of)\s*(\d+\.?\d*)", q)
            if m:
                parts.append(f'"{name}" = {m.group(1)}')

        return parts

    # ── Genre condition ────────────────────────────────────────
    def _genre_condition(self, q, col_lookup):
        genre_col = self._col_real_name(["genre", "category", "type"], col_lookup)
        if not genre_col:
            return []

        genres = [
            "drama", "action", "comedy", "horror", "thriller", "romance",
            "sci-fi", "science fiction", "history", "war", "crime", "animation",
            "biography", "fantasy", "mystery", "adventure", "family", "sport",
            "western", "musical", "documentary", "film-noir",
        ]
        for g in genres:
            if re.search(rf"\b{re.escape(g)}\b", q):
                label = "Sci-Fi" if g == "sci-fi" else ("Science Fiction" if g == "science fiction" else g.title())
                return [f'"{genre_col}" LIKE \'%{label}%\'']
        return []

    # ── Text conditions ────────────────────────────────────────
    def _text_conditions(self, q, columns):
        parts = []
        skip = {"genre", "year", "release_year", "released"}

        for col in columns:
            name = col["name"]
            nl   = name.lower()

            if nl in skip or col.get("type") in ("INTEGER", "REAL", "NUMERIC"):
                continue

            if nl == "director":
                m = re.search(
                    r"(?:directed by|director(?:\s+(?:is|named|called))?)\s+([a-z][a-z '.]+?)(?:\s+(?:and|or|with|in|from|where)|$)", q)
                if m:
                    parts.append(f'"{name}" LIKE \'%{m.group(1).strip()}%\'')
                continue

            if nl == "stars":
                m = re.search(
                    r"(?:starring|stars?|featuring|with actor|with actress|cast includes?)\s+([a-z][a-z '.]+?)(?:\s+(?:and|or|in|from|where)|$)", q)
                if m:
                    parts.append(f'"{name}" LIKE \'%{m.group(1).strip()}%\'')
                continue

            if nl == "title":
                m = re.search(
                    r"(?:title|movie|film)\s+(?:contains?|named?|called|like|with word)\s+[\"']?([a-z0-9 ]+?)[\"']?(?:\s|$)", q)
                if m:
                    parts.append(f'"{name}" LIKE \'%{m.group(1).strip()}%\'')
                continue

            if nl == "certificate":
                cert_map = {
                    "pg-13": "PG-13", "pg": "PG", " r ": "R",
                    "r rated": "R", "r-rated": "R", "nc-17": "NC-17",
                    "tv-pg": "TV-PG", "tv-14": "TV-14", "tv-ma": "TV-MA",
                    "not rated": "Not Rated", "passed": "Passed", "approved": "Approved",
                }
                for key, val in cert_map.items():
                    if key in q:
                        parts.append(f'"{name}" = \'{val}\'')
                        break

        return parts

    # ── SELECT cols ────────────────────────────────────────────
    def _select_cols(self, q, columns):
        found = []
        for col in columns:
            name = col["name"]
            for alias in self._col_aliases(name.lower()):
                if re.search(rf"\b{re.escape(alias)}\b", q) and name not in found:
                    found.append(name)
                    break
        return found

    # ── ORDER BY ───────────────────────────────────────────────
    def _order_by(self, q, columns):
        direction = ""
        if re.search(r"\b(highest|descending|desc|most|best|top|largest|greatest|popular|newest|latest|recent)\b", q):
            direction = "DESC"
        elif re.search(r"\b(lowest|ascending|asc|least|worst|smallest|oldest|earliest|first)\b", q):
            direction = "ASC"

        m = re.search(
            r"(?:order by|sort by|sorted by|ranked by|arrange by)\s+(\w[\w\s]*?)(?:\s+(asc|desc))?(?:\s|$)", q)
        if m:
            col_hint = m.group(1).strip()
            dir_hint = (m.group(2) or direction or "ASC").upper()
            col = self._find_col_by_hint(col_hint, columns)
            if col:
                return f'"{col}" {dir_hint}'

        if direction:
            col = self._best_num_col(q, columns)
            if col:
                return f'"{col}" {direction}'

        return ""

    # ── LIMIT ──────────────────────────────────────────────────
    def _limit(self, q):
        m = re.search(
            r"\btop\s+(\d+)\b|\bfirst\s+(\d+)\b|\blimit\s+(\d+)\b"
            r"|\b(\d+)\s+(?:movies?|films?|results?|records?|titles?|rows?)\b", q)
        if m:
            return next(g for g in m.groups() if g)
        return ""

    # ── Helpers ────────────────────────────────────────────────
    def _col_real_name(self, candidates, col_lookup):
        for c in candidates:
            if c in col_lookup:
                return col_lookup[c]["name"]
        return None

    def _best_num_col(self, q, columns):
        priority = ["rating", "score", "votes", "gross", "runtime", "year"]
        for p in priority:
            for col in columns:
                if p in col["name"].lower() and col.get("type") in ("INTEGER", "REAL", "NUMERIC"):
                    if any(a in q for a in self._col_aliases(col["name"].lower())):
                        return col["name"]
        for col in columns:
            if col.get("type") in ("INTEGER", "REAL", "NUMERIC"):
                return col["name"]
        return None

    def _find_col_by_hint(self, hint, columns):
        for col in columns:
            name = col["name"]
            if hint in name.lower() or name.lower() in hint:
                return name
            for alias in self._col_aliases(name.lower()):
                if alias in hint or hint in alias:
                    return name
        return None

    def _col_aliases(self, col_lower):
        SYNONYMS = {
            "title":          ["title", "movie", "film", "name", "show", "picture"],
            "year":           ["year", "released", "release year", "date", "when"],
            "runtime":        ["runtime", "duration", "length", "minutes", "mins"],
            "runtime  (min)": ["runtime", "duration", "length", "minutes", "mins"],
            "certificate":    ["certificate", "certification", "rated", "mpaa"],
            "genre":          ["genre", "category", "type", "kind"],
            "director":       ["director", "directed", "filmmaker"],
            "stars":          ["stars", "cast", "actors", "actress", "starring"],
            "rating":         ["rating", "score", "imdb", "imdb rating", "rate"],
            "votes":          ["votes", "reviews", "popularity"],
            "gross":          ["gross", "earnings", "revenue", "box office", "earned"],
        }
        for key, aliases in SYNONYMS.items():
            if col_lower == key or col_lower.startswith(key.split()[0]):
                return aliases
        return [col_lower.replace("_", " "), col_lower]
