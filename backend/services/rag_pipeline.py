"""
rag_pipeline.py — Schema-aware RAG using sentence-transformers + FAISS
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Few-shot examples injected into retrieval context
FEW_SHOTS = [
    {
        "question": "show all drama movies with rating above 8",
        "sql": 'SELECT * FROM "movies" WHERE "genre" LIKE \'%Drama%\' AND "rating" > 8 LIMIT 100'
    },
    {
        "question": "top 10 highest rated films",
        "sql": 'SELECT "title", "rating" FROM "movies" ORDER BY "rating" DESC LIMIT 10'
    },
    {
        "question": "how many action movies are there",
        "sql": 'SELECT COUNT(*) AS total FROM "movies" WHERE "genre" LIKE \'%Action%\''
    },
    {
        "question": "movies directed by nolan",
        "sql": 'SELECT "title", "year", "rating" FROM "movies" WHERE "director" LIKE \'%Nolan%\''
    },
    {
        "question": "average rating of horror movies",
        "sql": 'SELECT AVG("rating") AS avg_rating FROM "movies" WHERE "genre" LIKE \'%Horror%\''
    },
    {
        "question": "movies released between 1990 and 2000",
        "sql": 'SELECT * FROM "movies" WHERE "year" BETWEEN 1990 AND 2000 LIMIT 100'
    },
    {
        "question": "show title and gross ordered by gross descending",
        "sql": 'SELECT "title", "gross" FROM "movies" ORDER BY "gross" DESC LIMIT 100'
    },
    {
        "question": "movies with votes greater than 100000",
        "sql": 'SELECT "title", "votes", "rating" FROM "movies" WHERE "votes" > 100000 LIMIT 100'
    },
]


class RAGPipeline:
    def __init__(self):
        self._model    = None
        self._index    = None
        self._docs     = []   # list of text chunks
        self._ready    = False
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("RAG: embedding model loaded (all-MiniLM-L6-v2)")
        except ImportError:
            logger.warning("RAG: sentence-transformers not installed — RAG disabled")

    # ── Build index from schema ────────────────────────────────
    def build_index(self, schema: list):
        if not self._model:
            return
        try:
            import faiss
        except ImportError:
            logger.warning("RAG: faiss-cpu not installed — RAG disabled")
            return

        self._docs = []

        # 1. Schema chunks — one per column
        for table in schema:
            tname = table["name"]
            col_names = [c["name"] for c in table["columns"]]
            num_cols  = [c["name"] for c in table["columns"] if c.get("type") in ("INTEGER","REAL","NUMERIC")]
            txt_cols  = [c["name"] for c in table["columns"] if c.get("type") in ("TEXT","VARCHAR","TEXT")]

            # Full table description
            self._docs.append(
                f"Table '{tname}' has columns: {', '.join(col_names)}. "
                f"Numeric columns: {', '.join(num_cols) or 'none'}. "
                f"Text columns: {', '.join(txt_cols) or 'none'}."
            )

            # Per-column chunks for fine-grained retrieval
            for col in table["columns"]:
                self._docs.append(
                    f"Column '{col['name']}' in table '{tname}' is of type {col.get('type','TEXT')}."
                    + (" (primary key)" if col.get("pk") else "")
                )

        # 2. Few-shot example chunks
        for ex in FEW_SHOTS:
            self._docs.append(
                f"Example — Question: {ex['question']} | SQL: {ex['sql']}"
            )

        # 3. Embed and build FAISS index
        embeddings = self._model.encode(self._docs, convert_to_numpy=True, show_progress_bar=False)
        embeddings = embeddings.astype(np.float32)

        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatL2(dim)
        self._index.add(embeddings)
        self._ready = True
        logger.info(f"RAG: index built with {len(self._docs)} chunks")

    # ── Retrieve top-k relevant chunks ────────────────────────
    def retrieve(self, query: str, top_k: int = 6) -> str:
        if not self._ready or not self._model:
            return ""
        try:
            q_emb = self._model.encode([query], convert_to_numpy=True).astype(np.float32)
            _, indices = self._index.search(q_emb, top_k)
            results = [self._docs[i] for i in indices[0] if i < len(self._docs)]
            return "\n".join(results)
        except Exception as e:
            logger.error(f"RAG retrieve error: {e}")
            return ""

    @property
    def is_ready(self):
        return self._ready
