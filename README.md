# VoiceSQL — Talk to Your Data

A voice-powered natural language to SQL assistant. Upload any CSV or SQLite database and ask questions in plain English — or speak them aloud.

## Features

- 🎤 Voice input via Web Speech API
- 🧠 AI-powered SQL generation using Groq (Llama 3.3)
- 📊 Auto-generated bar, pie, and line charts
- 🔒 Read-only — no destructive queries allowed
- 🌙 Dark / light mode
- 📱 Fully responsive for mobile
- ⚡ Rule-based fallback if AI is unavailable

## Quick Start

**1. Clone the repo**
```bash
git clone https://github.com/your-username/voicesql.git
cd voicesql
```

**2. Install dependencies**
```bash
pip install -r backend/requirements.txt
```

**3. Set your API key**

Copy the example env file and add your key:
```bash
cp .env.example .env
```
Then open `.env` and set:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get a free key at [console.groq.com](https://console.groq.com)

**4. Run**
```bash
python backend/app.py
```

**5. Open browser**
```
http://localhost:5000
```

> On Windows you can just double-click `start.bat` after setting your key in `.env`

## Project Structure

```
voicesql/
├── backend/
│   ├── app.py                  # Flask server
│   ├── requirements.txt
│   └── services/
│       ├── text_to_sql.py      # Groq AI + rule-based SQL engine
│       ├── schema_analyzer.py  # CSV/SQLite schema parser
│       └── query_executor.py   # Safe SQL executor
├── frontend/
│   ├── index.html
│   ├── scripts/
│   │   ├── app.js              # Main app logic
│   │   ├── api.js              # Backend API calls
│   │   ├── chart-renderer.js   # Chart.js wrapper
│   │   └── voice.js            # Web Speech API
│   └── styles/
│       └── main.css
├── sample_KING.csv             # Sample movie dataset to test with
├── start.bat                   # Windows one-click launcher
└── .env.example                # Environment variable template
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
Movies after 2010 ordered by rating
Horror movies with votes greater than 50000
```

## Deploy to Render

1. Push to GitHub
2. Connect repo on [render.com](https://render.com)
3. Add environment variable: `GROQ_API_KEY`
4. Deploy — `render.yaml` handles the rest
