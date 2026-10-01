# Secure Local Filesystem REST API

A small FastAPI service for managing files inside a configured sandbox directory. Every user-provided path is resolved and checked against `BASE_DIRECTORY` before filesystem access, preventing path traversal outside the sandbox.

## Requirements

- Python 3.12+ for local development
- Docker for container execution

## Configuration

Copy `.env.example` to `.env` when running locally, or provide the variables directly:

```env
API_PORT=8080
BASE_DIRECTORY=./data
```

Do not commit a local `.env` file or secrets.

## Run locally

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:API_PORT = "8080"
$env:BASE_DIRECTORY = "./data"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The API is available at `http://localhost:8080`. Interactive API documentation is available at `/docs`.

## Run with Docker

Build the image from the project root:

```powershell
docker build -t file-manager-api .
```

Run it with the required port and sandbox mount:

```powershell
docker run -p 8080:8080 -e API_PORT=8080 -e BASE_DIRECTORY=/app/data -v ${PWD}/data:/app/data file-manager-api
```

The API is available at `http://localhost:8080`.

## Run tests

From the project root, with the virtual environment activated:

```powershell
python -m pytest -q
```

## API endpoints

All paths are relative to `BASE_DIRECTORY`.

### List a directory

`GET /files?path=documents`

The `path` query parameter is optional. The response is sorted with directories first, then files, alphabetically within each group.

```json
[
  {"name": "reports", "type": "directory", "size": 0},
  {"name": "readme.txt", "type": "file", "size": 48}
]
```

### Search for files

`GET /search?query=report&path=documents`

`query` is required and `path` is optional. The response contains matching file paths relative to `BASE_DIRECTORY`.

```json
["documents/report.pdf"]
```

### Copy a file or directory

`POST /files/copy`

```json
{"from": "documents/report.pdf", "to": "archive/report.pdf"}
```

Response:

```json
{"message": "Copied successfully from 'documents/report.pdf' to 'archive/report.pdf'"}
```

### Move a file or directory

`POST /files/move`

```json
{"from": "documents/report.pdf", "to": "archive/report.pdf"}
```

Response:

```json
{"message": "Moved successfully from 'documents/report.pdf' to 'archive/report.pdf'"}
```

### Delete a file or directory

`DELETE /files?path=documents/report.pdf`

Response:

```json
{"message": "Deleted successfully: 'documents/report.pdf'"}
```

## Errors

Errors use this structure:

```json
{"error": {"message": "..."}}
```

- `403`: the resolved path is outside `BASE_DIRECTORY`.
- `404`: the requested source or directory does not exist.
- `409`: copy or move would overwrite an existing destination.
- `400`: the request contains invalid or missing path data.

## Project layout

- `app/main.py`: API routes, path validation, and filesystem operations.
- `data/`: example sandbox contents.
- `Dockerfile`: production container definition.
- `.env.example`: required environment variables.
