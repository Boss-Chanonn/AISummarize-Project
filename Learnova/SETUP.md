# Learnova Setup (Mac + Windows)

## 1) Install Required Tools
- Git
- Docker Desktop

## 2) Clone Project
```bash
git clone <repo-url>
cd <repo-name>/Learnova
```

## 3) Create `.env` in `Learnova/`
```env
MONGO_URL=<your-mongodb-atlas-url>
DATABASE_NAME=learnova
SECRET_KEY=<your-secret>
ALLOWED_ORIGINS=http://localhost:8000
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://100.116.106.17:11434
OLLAMA_MODEL=gpt-oss:120b-cloud
OLLAMA_TIMEOUT_SECONDS=300
```

## 4) Prepare Ollama Model
Start stack:
```bash
docker compose up -d --build
```

This compose setup mounts your host `~/.ollama` into the container.
If you are already signed in on host, container reuses that session.

If needed, login once inside container:
```bash
docker compose exec ollama ollama signin
```

Pull model once:
```bash
docker compose exec ollama ollama pull gpt-oss:120b-cloud
```

Quick test (from host):

### Mac / Linux (Terminal)
```bash
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss:120b-cloud","prompt":"Respond with exactly: ok","stream":false}'
```

### Windows (PowerShell)
```powershell
curl.exe -s http://localhost:11434/api/generate -H "Content-Type: application/json" -d "{\"model\":\"gpt-oss:120b-cloud\",\"prompt\":\"Respond with exactly: ok\",\"stream\":false}"
```

Expected: response contains `"response":"ok"`.

## 5) Run App with Docker
From `Learnova/`:
```bash
docker compose up -d
```

Open:
```text
http://localhost:8000
```

## 6) If You Changed `.env` (Reload Config)
Use recreate to ensure new env is loaded:
```bash
docker compose up -d --force-recreate app
```

## 7) Common Errors (Quick Fix)
- `no configuration file provided: not found`
  - Run command inside `Learnova/` or specify file:
  - `docker compose -f /absolute/path/to/Learnova/docker-compose.yml up -d --force-recreate app`
- Ollama not responding
  - Check Ollama container: `docker compose logs ollama --tail 100`
  - Verify model exists: `docker compose exec ollama ollama list`
- MongoDB connection error
  - Recheck `MONGO_URL` and Atlas IP allowlist.
