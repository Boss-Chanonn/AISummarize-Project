# Learnova — Local Setup Guide

A step-by-step guide for running Learnova on a new machine.

---

## Prerequisites

Install the following before you begin:

| Tool | Purpose | Download |
|---|---|---|
| Git | Clone the repository | https://git-scm.com |
| Docker Desktop | Run the application in a container | https://www.docker.com/products/docker-desktop |
| Ollama *(optional)* | Run the local AI model for summarisation and quiz generation | https://ollama.com |

> **Note:** You do **not** need to install Python manually. Docker handles everything inside the container.

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>/Learnova
```

---

## Step 2 — Create the `.env` File

The `.env` file is **not included in the repository** (it is listed in `.gitignore` for security reasons).  
You must create it yourself inside the `Learnova/` folder.

Create a file named `.env` with the following content:

```env
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
DATABASE_NAME=learnova
SECRET_KEY=<any-long-random-string>
ALLOWED_ORIGINS=http://localhost:8000
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gpt-oss:120b-cloud
OLLAMA_TIMEOUT_SECONDS=300
```

### Variable Reference

| Variable | Description |
|---|---|
| `MONGO_URL` | MongoDB Atlas connection string. Get it from your Atlas cluster → **Connect** → **Drivers** |
| `DATABASE_NAME` | Name of the MongoDB database. Keep as `learnova` unless you changed it |
| `SECRET_KEY` | A secret string used to sign JWT tokens. Use any long random string |
| `ALLOWED_ORIGINS` | CORS allowed origin. Keep as `http://localhost:8000` for local dev |
| `OLLAMA_ENABLED` | Set to `true` to use Ollama AI, `false` to disable AI features |
| `OLLAMA_BASE_URL` | URL where Ollama is running. `host.docker.internal` points to your machine from inside Docker |
| `OLLAMA_MODEL` | The Ollama model to use. Must match the model you pulled (e.g. `gpt-oss:120b-cloud`) |
| `OLLAMA_TIMEOUT_SECONDS` | Seconds to wait for Ollama to respond before timing out |

---

## Step 3 — Set Up Ollama (Optional — Required for AI Features)

Ollama runs **directly on your machine**, not inside Docker.

```bash
# 1. Start the Ollama server
ollama serve

# 2. Pull the model (only needed once — downloads ~4 GB)
ollama pull gpt-oss:120b-cloud
```

Leave `ollama serve` running in a separate terminal while the app is running.

> If you set `OLLAMA_ENABLED=false` in `.env`, you can skip this step.  
> AI summaries and quiz generation will be unavailable, but the rest of the app will still work.

---

## Step 4 — Build and Run with Docker

Make sure Docker Desktop is running, then:

```bash
# From inside the Learnova/ folder
docker compose up --build
```

The first run will take a few minutes while Docker downloads the Python image and installs dependencies.  
Subsequent runs are much faster.

### What Docker does

```
docker compose up --build
│
├── Reads Dockerfile
│     ├── Pulls python:3.10-slim base image
│     ├── Installs all packages from requirements.txt
│     └── Copies project files into the container
│
└── Starts container (learnova-app-1)
      ├── Exposes port 8000
      ├── Loads environment variables from .env
      ├── Mounts your local folder so code changes reload instantly
      └── Runs: uvicorn backend.main:app --reload
```

---

## Step 5 — Open the App

Once Docker is running, open your browser and go to:

```
http://localhost:8000
```

---

## Stopping the App

```bash
# Press Ctrl+C in the terminal running docker compose

# Or stop and remove the container:
docker compose down
```

---

## Common Issues

| Problem | Fix |
|---|---|
| `MONGO_URL` connection error | Check your Atlas IP allowlist — add `0.0.0.0/0` for local dev, or your specific IP |
| Ollama not responding | Make sure `ollama serve` is running on your machine before starting Docker |
| Port 8000 already in use | Stop any other service on port 8000, or change the port mapping in `docker-compose.yml` |
| Docker not found | Make sure Docker Desktop is installed and running (check the system tray icon) |
| `.env` not loaded | Make sure the file is named exactly `.env` (no `.txt` extension) and is inside the `Learnova/` folder |

---

## Project Structure (Quick Reference)

```
Learnova/
├── backend/              # FastAPI application
│   ├── main.py           # App entry point, routes registered here
│   ├── routes/           # API route handlers (auth, history, upload, etc.)
│   ├── models/           # Pydantic models
│   ├── database/         # MongoDB connection
│   └── middleware/       # Auth middleware, security
├── frontend/             # Static HTML/CSS/JS (served by FastAPI)
│   ├── index.html        # Login page
│   ├── dashboard.html    # Main dashboard
│   ├── upload.html       # Upload + Quiz page
│   ├── history.html      # History page
│   ├── results.html      # Quiz results page
│   ├── css/              # Stylesheets
│   └── js/               # Shared JavaScript (app.js, animations.js)
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker service configuration
├── requirements.txt      # Python dependencies
└── .env                  # ⚠️ NOT in repo — you must create this yourself
```
