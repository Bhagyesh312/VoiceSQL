"""
Universal Voice-to-SQL Assistant — Flask Backend
"""
import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Load .env file if present
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
_load_env()

from services.schema_analyzer import SchemaAnalyzer
from services.query_executor import QueryExecutor
from services.text_to_sql import TextToSQL
from services.rag_pipeline import RAGPipeline

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
FRONTEND_DIR  = os.path.join(BASE_DIR, "..", "frontend")
ALLOWED_EXT   = {"csv", "db", "sqlite", "sqlite3"}

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["UPLOAD_FOLDER"]    = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
CORS(app, resources={r"/api/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

schema_analyzer = SchemaAnalyzer(UPLOAD_FOLDER)
query_executor  = QueryExecutor()
text_to_sql     = TextToSQL(anthropic_api_key=os.environ.get("GROQ_API_KEY"))
rag             = RAGPipeline()


def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename or not allowed(f.filename):
        return jsonify({"error": f"Unsupported type. Allowed: {', '.join(ALLOWED_EXT)}"}), 400

    filename = secure_filename(f.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(path)
    try:
        result = schema_analyzer.analyze(path, filename)
        # Build RAG index from extracted schema
        rag.build_index(result["tables"])
        return jsonify({"message": "Uploaded successfully", "filename": filename,
                        "tables": result["tables"], "db_path": result["db_path"]}), 200
    except Exception as e:
        logger.exception("Upload failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def query():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip()
    db_path  = body.get("db_path", "").strip()
    schema   = body.get("schema", [])

    if not question: return jsonify({"error": "'question' is required"}), 400
    if not db_path:  return jsonify({"error": "'db_path' is required"}), 400
    if not os.path.exists(db_path): return jsonify({"error": "DB not found, re-upload"}), 400

    try:
        # Retrieve relevant schema context via RAG before calling LLM
        rag_context = rag.retrieve(question) if rag.is_ready else ""
        sql_result = text_to_sql.convert(question=question, schema=schema, rag_context=rag_context)
        if not sql_result["success"]:
            return jsonify({"error": "Could not understand question",
                            "suggestions": sql_result.get("suggestions", [])}), 422

        sql    = sql_result["sql"]
        source = sql_result["source"]
        result = query_executor.execute(db_path=db_path, sql=sql)
        chart  = _suggest_chart(result["columns"], result["rows"])

        return jsonify({"sql": sql, "columns": result["columns"], "rows": result["rows"],
                        "row_count": len(result["rows"]), "source": source,
                        "chart_suggestion": chart}), 200
    except PermissionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Query failed")
        return jsonify({"error": str(e)}), 500


@app.route("/api/suggestions", methods=["POST"])
def suggestions():
    body   = request.get_json(silent=True) or {}
    schema = body.get("schema", [])
    return jsonify({"suggestions": _gen_suggestions(schema)}), 200


def _suggest_chart(columns, rows):
    if not rows or len(columns) < 2: return None
    try:
        vals = [r[1] for r in rows[:10] if r[1] is not None]
        if all(isinstance(v, (int, float)) for v in vals):
            return "pie" if len(rows) <= 6 else "bar"
    except: pass
    return None


def _gen_suggestions(schema):
    out = []
    for t in schema:
        n  = t.get("name", "table")
        cols = t.get("columns", [])
        nums = [c["name"] for c in cols if c.get("type") in ("INTEGER","REAL","NUMERIC")]
        txts = [c["name"] for c in cols if c.get("type") in ("TEXT","VARCHAR")]
        out += [f"Show all records from {n}", f"How many rows are in {n}?"]
        if nums: out += [f"What is the average {nums[0]} in {n}?",
                         f"Show {n} where {nums[0]} is greater than 50"]
        if txts and nums: out.append(f"Show {txts[0]} and {nums[0]} from {n} ordered by {nums[0]}")
    return out[:8]


if __name__ == "__main__":
    port  = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    logger.info(f"Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
