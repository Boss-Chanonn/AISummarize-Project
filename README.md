# Learnova — AI Learning Platform

An AI-powered learning platform that summarises uploaded documents, generates quizzes, and provides personalised study recommendations.

Built with **FastAPI** + **MongoDB Atlas** + **Ollama (LLaMA 3)** + **Docker**.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.10) |
| Frontend | HTML / CSS / Vanilla JS (served by FastAPI) |
| Database | MongoDB Atlas (cloud) |
| AI | Ollama — llama3:latest |
| Auth | JWT + bcrypt + token blocklist |
| Container | Docker + Docker Compose |

---

## Prerequisites

Before running this project you need:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [Ollama](https://ollama.com) installed on your machine (for local AI)
- A [MongoDB Atlas](https://www.mongodb.com/atlas) account with a free cluster

---

## Quick Start (For Anyone Running This Project)

### Step 1 — Download the project files

You need two files in the same folder:
- `docker-compose.yml`
- `.env` (you must create this — see Step 2)

### Step 2 — Create your `.env` file

Create a file named `.env` in the same folder as `docker-compose.yml`.
Copy the template below and fill in your own values:

```env
MONGO_URL=mongodb+srv://YOUR_USERNAME:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/?appName=Cluster0
DATABASE_NAME=learnova
SECRET_KEY=replace-this-with-a-long-random-string-at-least-32-chars
ALLOWED_ORIGINS=http://localhost:8000
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3:latest
OLLAMA_TIMEOUT_SECONDS=300
```

> **MONGO_URL** — Get this from MongoDB Atlas → your cluster → Connect → Drivers
>
> **SECRET_KEY** — Type any long random string, e.g. `x7k!mP2qL9nR4vZ0wT8uA3cE6fH1jB5y`
>
> **Never share your `.env` file with anyone.**

### Step 3 — Pull the AI model (first time only)

Make sure Ollama is running on your machine, then open a terminal and run:

```bash
ollama pull llama3:latest
```

This downloads the LLaMA 3 model (~4.7 GB). You only need to do this once.

### Step 4 — Start the application

Open a terminal in the folder containing `docker-compose.yml` and run:

```bash
docker-compose up -d
```

Docker will automatically download the application image and start it.
Wait about 10–15 seconds for startup to complete.

### Step 5 — Open in browser

Go to: **http://localhost:8000**

You should see the Learnova landing page. Register an account and start uploading documents.

### Stopping the application

```bash
docker-compose down
```

---

## For Developers — Running from Source

### Clone and set up

```bash
git clone https://github.com/YOUR_USERNAME/learnova.git
cd learnova/Learnova
```

Create your `.env` file as described in Step 2 above.

### Build and run with Docker

```bash
# First time (or after changing requirements.txt)
docker-compose up --build -d

# Subsequent runs
docker-compose up -d
```

### View logs

```bash
docker logs learnova-app-1 -f
```

---

## Project Structure

```
Learnova/
├── backend/
│   ├── main.py                  ← FastAPI app entry point
│   ├── routes/
│   │   ├── auth.py              ← Register, login, logout, profile
│   │   ├── upload.py            ← Document upload + AI processing
│   │   ├── history.py           ← History CRUD + quiz submission
│   │   ├── content.py           ← Results + learning modules
│   │   ├── user.py              ← User profile stats
│   │   ├── admin.py             ← Admin management routes
│   │   └── sysadmin.py          ← System health + logs
│   ├── services/
│   │   └── ollama_service.py    ← AI summary, quiz, analysis generation
│   ├── middleware/
│   │   ├── auth_middleware.py   ← JWT verification + RBAC
│   │   └── security.py         ← Security headers middleware
│   ├── models/
│   │   └── user.py              ← Pydantic models
│   └── database/
│       └── db.py                ← MongoDB Atlas connection
├── frontend/
│   ├── landing.html             ← Public landing page
│   ├── index.html               ← Dashboard
│   ├── upload.html              ← Upload & AI summarise
│   ├── history.html             ← Document history
│   ├── results.html             ← Quiz results
│   ├── module.html              ← Learning modules
│   ├── css/style.css
│   └── js/
│       ├── app.js
│       ├── animations.js
│       └── mock-api.js
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env                         ← Not committed — create your own
```

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login, returns JWT |
| POST | `/api/auth/logout` | Invalidate token |
| GET | `/api/user/profile` | Dashboard stats |
| POST | `/api/upload` | Upload file, get AI summary + quiz |
| GET | `/api/history` | All uploaded documents |
| POST | `/api/history/{id}/submit-quiz` | Submit quiz answers |
| GET | `/api/results?id=` | Quiz results + analysis |
| GET | `/api/modules?historyId=` | Learning module links |

Full API docs available at: **http://localhost:8000/docs**

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URL` | ✅ | MongoDB Atlas connection string |
| `DATABASE_NAME` | ✅ | Database name (default: `learnova`) |
| `SECRET_KEY` | ✅ | JWT signing secret — use a strong random string |
| `OLLAMA_ENABLED` | ✅ | Set `true` to enable AI, `false` to use fallback |
| `OLLAMA_BASE_URL` | ✅ | Ollama URL — `http://host.docker.internal:11434` |
| `OLLAMA_MODEL` | ✅ | Model name — `llama3:latest` |
| `OLLAMA_TIMEOUT_SECONDS` | ✅ | AI request timeout — `300` recommended |
| `ALLOWED_ORIGINS` | ✅ | CORS origins — `http://localhost:8000` |
