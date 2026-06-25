# Learnova (Final)

Learnova is an AI-powered learning platform for uploading documents, generating summaries/quizzes, and tracking study progress.

## What You Need

- Docker Desktop (must be running)
- MongoDB Atlas connection string
- Ollama endpoint/model (local or remote)

## Fastest Way To Run

From the project root:

```bash
./run.sh
```

This command will:

1. Check Docker + Docker Compose availability
2. Check `.env` in `Learnova/`
3. Build and start the app container
4. Show useful URLs

## First-Time Setup

1. Make scripts executable (one time):

```bash
chmod +x run.sh Learnova/run.sh
```

2. Create env file (if not created yet):

```bash
cp Learnova/.env.example Learnova/.env
```

3. Edit `Learnova/.env` and set required values:

- `MONGO_URL`
- `SECRET_KEY`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

Recommended local defaults are already included in `.env.example`.

## Script Commands

Main entrypoint (from root):

```bash
./run.sh [command]
```

Available commands:

- `up` (default): build + start project
- `down`: stop project
- `restart`: restart containers
- `logs`: follow app logs
- `status`: show container status
- `doctor`: check prerequisites and env
- `help`: show command usage

You can also run the same commands directly in `Learnova/`:

```bash
cd Learnova
./run.sh up
```

## URLs

- App: http://localhost:8000
- Swagger API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## Typical Workflow

Start project:

```bash
./run.sh
```

Check logs:

```bash
./run.sh logs
```

Stop project:

```bash
./run.sh down
```

## Notes

- If dependencies changed, `up` already rebuilds images.
- If `.env` changed, run `./run.sh restart`.
- Keep `.env` private and never commit secrets.