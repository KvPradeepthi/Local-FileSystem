# Secure Local Filesystem REST API

A secure FastAPI REST service for managing files and directories inside a configured sandbox directory. Every user-provided path is strictly resolved and validated against `BASE_DIRECTORY` before filesystem access, preventing path traversal attacks outside the sandbox.

---

## 1. Prerequisites

- **Python 3.12+** (for local development and testing)
- **Docker** (for containerized execution)

---

## 2. Configuration

Copy `.env.example` to `.env` when running locally, or supply environment variables directly:

```env
API_PORT=8080
BASE_DIRECTORY=./data
```

> **Security Note:** Do not commit a local `.env` file, credentials, or secrets to the repository.

---

## 3. Local Setup Instructions

From the project root:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# or on Windows PowerShell: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Local Run Command

Run using Uvicorn from the project root:

```bash
export API_PORT=8080
export BASE_DIRECTORY=./data
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

*(On Windows PowerShell)*:
```powershell
$env:API_PORT = "8080"
$env:BASE_DIRECTORY = "./data"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The application is accessible at:
- **Base URL:** `http://localhost:8080`
- **Interactive OpenAPI Documentation:** `http://localhost:8080/docs`

---

## 5. Docker Build & Run Commands

### Build Image
```bash
docker build -t file-manager-api .
```

### Run Container
```bash
docker run -p 8080:8080 \
  -e API_PORT=8080 \
  -e BASE_DIRECTORY=/app/data \
  -v $(pwd)/data:/app/data \
  file-manager-api
```

*(On Windows PowerShell)*:
```powershell
docker run -p 8080:8080 -e API_PORT=8080 -e BASE_DIRECTORY=/app/data -v ${PWD}/data:/app/data file-manager-api
```

---

## 6. Testing Instructions

From the project root with dependencies installed:

```bash
python -m pytest tests -v
```

This verifies deterministic sorting, search, file/directory copy, move, deletion, conflict rejection (409), not-found handling (404), and path traversal prevention (403).

---

## 7. API Endpoints & Specification

All paths are relative to `BASE_DIRECTORY`. Leading slashes or directory traversal sequences (`..`) are rejected.

### 1. List Files and Directories
- **Endpoint:** `GET /files`
- **Method:** `GET`
- **Query Parameters:**
  - `path` *(string, optional, default: "")*: Relative path to a directory within `BASE_DIRECTORY`.
- **Behavior:** Deterministic directory-first alphabetical listing (directories first alphabetically, then files alphabetically).
- **Example Request:**
  ```http
  GET /files?path=documents HTTP/1.1
  Host: localhost:8080
  ```
- **Example Success Response (200 OK):**
  ```json
  [
    {"name": "reports", "type": "directory", "size": 0},
    {"name": "report.pdf", "type": "file", "size": 24}
  ]
  ```

---

### 2. Search Files
- **Endpoint:** `GET /search`
- **Method:** `GET`
- **Query Parameters:**
  - `query` *(string, required, min length 1)*: Case-insensitive filename search term.
  - `path` *(string, optional, default: "")*: Relative subfolder to scope the recursive search.
- **Behavior:** Recursively searches files from the specified root and returns relative POSIX paths matching the query.
- **Example Request:**
  ```http
  GET /search?query=report&path=documents HTTP/1.1
  Host: localhost:8080
  ```
- **Example Success Response (200 OK):**
  ```json
  [
    "documents/report.pdf"
  ]
  ```

---

### 3. Copy File or Directory
- **Endpoint:** `POST /files/copy`
- **Method:** `POST`
- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "from": "documents/report.pdf",
    "to": "archive/report.pdf"
  }
  ```
  *(Note: `"from_path"` is also accepted as an alias for `"from"`)*
- **Example Success Response (200 OK):**
  ```json
  {
    "message": "Copied successfully from 'documents/report.pdf' to 'archive/report.pdf'"
  }
  ```

---

### 4. Move File or Directory
- **Endpoint:** `POST /files/move`
- **Method:** `POST`
- **Request Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "from": "documents/report.pdf",
    "to": "archive/report.pdf"
  }
  ```
  *(Note: `"from_path"` is also accepted as an alias for `"from"`)*
- **Example Success Response (200 OK):**
  ```json
  {
    "message": "Moved successfully from 'documents/report.pdf' to 'archive/report.pdf'"
  }
  ```

---

### 5. Delete File or Directory
- **Endpoint:** `DELETE /files`
- **Method:** `DELETE`
- **Query Parameters:**
  - `path` *(string, required)*: Relative path of the file or directory to delete.
- **Example Request:**
  ```http
  DELETE /files?path=documents/report.pdf HTTP/1.1
  Host: localhost:8080
  ```
- **Example Success Response (200 OK):**
  ```json
  {
    "message": "Deleted successfully: 'documents/report.pdf'"
  }
  ```

---

## 8. Error Responses & Status Codes

All errors return a consistent JSON payload:

```json
{
  "error": {
    "message": "Description of the error"
  }
}
```

| Status Code | Meaning | Condition |
| :--- | :--- | :--- |
| **400 Bad Request** | Invalid Input | Missing required relative path, invalid payload, or attempt to modify the root directory. |
| **403 Forbidden** | Access Denied | Path traversal attempt (e.g. `../`, `../../`, `../../../`) or absolute path outside `BASE_DIRECTORY`. |
| **404 Not Found** | Not Found | Source file/directory does not exist, or path is not a directory for listing/search. |
| **409 Conflict** | Conflict | Destination file or directory already exists during copy or move operations. |

---

## 9. Security & Path Traversal Protection

Path resolution enforces sandboxing without naive string replacements:
1. Rejects inputs that begin with root slashes (`/` or `\`) or drive letters.
2. Resolves relative paths using `(BASE_DIRECTORY / candidate).resolve()`.
3. Verifies that the resolved absolute path is strictly within the allowed boundary using `resolved.relative_to(BASE_DIRECTORY)`.
4. Any escape attempt (such as `../`, `../../`, `../../../`, or symlink tricks) raises a `PermissionError` and returns HTTP `403 Forbidden`.

---

## 10. Project Structure

```text
file-manager-api/
├── Dockerfile
├── .dockerignore
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   └── main.py
├── data/
│   ├── documents/
│   │   └── report.pdf
│   └── readme.txt
└── tests/
    └── test_api.py
```
