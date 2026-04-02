---
title: VoiceSQL
emoji: 🎤
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# VoiceSQL — Talk to Your Data

A voice-powered natural language to SQL assistant. Upload any CSV or SQLite database and ask questions in plain English — or speak them aloud. Get instant results with charts, pagination, and CSV export.

![Python](https://img.shields.io/badge/Python-Flask-blue) ![AI](https://img.shields.io/badge/AI-Groq%20Llama%203.3-orange) ![RAG](https://img.shields.io/badge/RAG-FAISS%20%2B%20sentence--transformers-purple) ![License](https://img.shields.io/badge/license-MIT-green) [![Live Demo](https://img.shields.io/badge/🤗%20Live%20Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/BhagyeshShah11/VoiceSQL)

**🚀 Live Demo: [huggingface.co/spaces/BhagyeshShah11/VoiceSQL](https://huggingface.co/spaces/BhagyeshShah11/VoiceSQL)**

## Features

- 🎤 Voice input via Web Speech API
- 🧠 AI-powered SQL generation using Groq (Llama 3.3-70b)
- � RAG pipeline — schema-aware context retrieval using FAISS + sentence-transformers
- �📊 Auto-generated bar, pie, and line charts
- 🔒 Read-only — no destructive queries allowed
- 🌙 Dark / light mode toggle
- 📱 Fully responsive — works on mobile
- ⚡ Rule-based fallback if AI is unavailable
- 📄 Pagination for large result sets
- 💾 Export results as CSV

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | HTML, CSS, Vanilla JS |
| Backend | Python, Flask |
| AI | Groq API (Llama 3.3-70b-versatile) |
| RAG | FAISS + sentence-transformers (all-MiniLM-L6-v2) |
| Charts | Chart.js |
| Voice | Web Speech API |

## How RAG Works

When you ask a question, before calling the LLM the system:
1. Embeds your question into a vector using `all-MiniLM-L6-v2`
2. Searches a FAISS index for the most relevant schema facts and few-shot examples
3. Injects that context into the Groq prompt for more accurate SQL generation

The index is built automatically after every file upload.

## Quick Start (Local)

**1. Clone the repo**
```bash
git clone https://github.com/Bhagyesh312/VoiceSQL.git
cd VoiceSQL
```

**2. Install dependencies**
```bash
pip install -r backend/requirements.txt
```
> First run will download the RAG embedding model (~90MB, one-time only)

**3. Set your API key**
```bash
cp .env.example .env
```
Open `.env` and set:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get a free key at [console.groq.com](https://console.groq.com) — no credit card needed.

**4. Run**
```bash
python backend/app.py
```

**5. Open browser**
```
http://localhost:5000
```

> On Windows — double-click `start.bat` after setting your key in `.env`

## Deploy to Render (Free)

This project is pre-configured for [Render.com](https://render.com).

1. Fork this repo to your GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Add environment variable: `GROQ_API_KEY` = your key
5. Click Deploy — `render.yaml` handles the rest

> Netlify will NOT work — this project requires a Python backend. Use Render, Railway, or Koyeb.

## Project Structure

```
VoiceSQL/
├── backend/
│   ├── app.py                  # Flask server & API routes
│   ├── requirements.txt        # Python dependencies
│   └── services/
│       ├── rag_pipeline.py     # FAISS + sentence-transformers RAG
│       ├── text_to_sql.py      # Groq AI + rule-based SQL engine
│       ├── schema_analyzer.py  # CSV/SQLite schema parser
│       └── query_executor.py   # Safe read-only SQL executor
├── frontend/
│   ├── index.html
│   ├── scripts/
│   │   ├── app.js
│   │   ├── api.js
│   │   ├── chart-renderer.js
│   │   └── voice.js
│   └── styles/
│       └── main.css
├── sample_KING.csv             # Sample movie dataset
├── start.bat                   # Windows launcher
├── .env.example                # Environment variable template
├── render.yaml                 # Render.com deployment config
└── Procfile                    # Process file for deployment
```

## Example Queries

Try these with the included `sample_KING.csv` movie dataset:

```
Show all titles released in 1994
Drama movies with rating above 8
Top 10 highest rated films
Movies between 1990 and 2000
How many action movies are there?
Movies directed by Nolan
Average rating of horror movies
Movies with votes greater than 100000
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key for AI SQL generation | Yes |

## License

MIT
