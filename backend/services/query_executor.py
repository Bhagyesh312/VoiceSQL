"""Query Executor — SELECT-only safe SQL execution"""
import re, sqlite3, logging

logger = logging.getLogger(__name__)

class QueryExecutor:
    FORBIDDEN = {"DROP","DELETE","UPDATE","INSERT","ALTER","CREATE","REPLACE",
                 "TRUNCATE","ATTACH","DETACH","PRAGMA","VACUUM","REINDEX","LOAD_EXTENSION"}
    MAX_ROWS = 1000

    def execute(self, db_path, sql):
        sql = self._clean(sql)
        if not sql.strip(): raise ValueError("Empty SQL")
        self._validate(sql)
        return self._run(db_path, sql)

    def _validate(self, sql):
        first = sql.strip().split()[0].upper()
        if first != "SELECT":
            raise PermissionError(f"Only SELECT allowed. Got: '{first}'")
        for tok in re.split(r"[\s,;()\[\]]+", sql):
            if tok.upper() in self.FORBIDDEN:
                raise PermissionError(f"Forbidden keyword: '{tok}'")
        if ";" in sql.rstrip(";"):
            raise PermissionError("Multiple statements not allowed")
        if re.search(r"--|/\*", sql):
            raise PermissionError("SQL comments not allowed")

    def _run(self, db_path, sql):
        try:    conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
        except: conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = [self._serialize(r) for r in cur.fetchmany(self.MAX_ROWS)]
            logger.info(f"Query OK: {len(rows)} rows, {len(cols)} cols")
            return {"columns": cols, "rows": rows}
        except sqlite3.Error as e:
            raise RuntimeError(f"DB error: {e}")
        finally:
            conn.close()

    def _clean(self, sql):
        sql = sql.strip()
        sql = re.sub(r"^```[a-zA-Z]*\n?", "", sql)
        sql = re.sub(r"```$", "", sql)
        return sql.strip()

    def _serialize(self, row):
        out = []
        for v in row:
            if isinstance(v, bytes): out.append(v.decode("utf-8", errors="replace"))
            elif isinstance(v, float) and v != v: out.append(None)
            else: out.append(v)
        return out
