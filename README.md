# HeyThere (Render-ready)

## Deploy on Render
1. Set environment variables (at least `SESSION_SECRET`, `DATABASE_URL`, any mail credentials, and optional AWS settings).
2. Use the provided `Procfile` and `requirements.txt`.
3. Render Start Command is defined by `Procfile`: `web: gunicorn wsgi:app`.

## Local Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_ENV=development
flask db upgrade  # after configuring DATABASE_URL or use sqlite for dev
gunicorn wsgi:app
```
