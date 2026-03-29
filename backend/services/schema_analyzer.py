"""Schema Analyzer — CSV to SQLite + schema extraction"""
import os, re, sqlite3, logging
import pandas as pd

logger = logging.getLogger(__name__)

class SchemaAnalyzer:
    DTYPE_MAP = {"int64":"INTEGER","int32":"INTEGER","float64":"REAL","float32":"REAL","bool":"INTEGER","object":"TEXT"}

    def __init__(self, upload_folder):
        self.upload_folder = upload_folder

    def analyze(self, file_path, original_filename):
        ext = original_filename.rsplit(".", 1)[-1].lower()
        db_path = self._csv_to_sqlite(file_path, original_filename) if ext == "csv" else file_path
        return {"db_path": db_path, "tables": self._extract_schema(db_path)}

    def _csv_to_sqlite(self, csv_path, original_filename):
        table_name  = self._to_table_name(original_filename)
        db_path     = os.path.join(self.upload_folder, original_filename.rsplit(".",1)[0] + ".db")
        try:    df = pd.read_csv(csv_path, encoding="utf-8")
        except: df = pd.read_csv(csv_path, encoding="latin-1")
        df.columns = [self._clean_col(c) for c in df.columns]
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()
        conn = sqlite3.connect(db_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.commit(); conn.close()
        logger.info(f"CSV→SQLite: {len(df)} rows → '{table_name}'")
        return db_path

    def _extract_schema(self, db_path):
        tables = []
        conn   = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur    = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        for row in cur.fetchall():
            name = row["name"]
            cur.execute(f"PRAGMA table_info('{name}')")
            cols = [{"name": r["name"], "type": self._norm_type(r["type"] or "TEXT"),
                     "nullable": not r["notnull"], "pk": bool(r["pk"])} for r in cur.fetchall()]
            cur.execute(f"SELECT COUNT(*) as c FROM '{name}'")
            count = cur.fetchone()["c"]
            cur.execute(f"SELECT * FROM '{name}' LIMIT 5")
            samples = [list(r) for r in cur.fetchall()]
            tables.append({"name": name, "columns": cols, "row_count": count, "sample_rows": samples})
        conn.close()
        return tables

    def _to_table_name(self, filename):
        n = re.sub(r"[^a-z0-9_]", "_", filename.rsplit(".",1)[0].lower())
        n = re.sub(r"_+", "_", n).strip("_")
        return ("t_" + n) if n and n[0].isdigit() else (n or "data")

    def _clean_col(self, col):
        c = re.sub(r"[^a-z0-9_]", "_", str(col).strip().lower())
        c = re.sub(r"_+", "_", c).strip("_")
        return ("col_" + c) if c and c[0].isdigit() else (c or "column")

    def _norm_type(self, t):
        t = t.upper()
        if "INT" in t: return "INTEGER"
        if any(x in t for x in ("CHAR","CLOB","TEXT")): return "TEXT"
        if any(x in t for x in ("REAL","FLOA","DOUB")): return "REAL"
        if any(x in t for x in ("NUMERIC","DECIMAL")): return "NUMERIC"
        return "TEXT"
