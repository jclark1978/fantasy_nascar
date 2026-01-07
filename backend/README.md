Backend prototype

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Set `RAPIDAPI_KEY` in your environment to enable live RapidAPI calls. If `RAPIDAPI_KEY` is not set the server will use bundled sample data.

The default SQLite DB file is `fantasy_nascar.db` in the repo root.
