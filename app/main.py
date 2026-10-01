from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, model_validator


API_PORT = int(os.getenv("API_PORT", "8080"))
BASE_DIRECTORY = Path(os.getenv("BASE_DIRECTORY", "./data")).expanduser().resolve()
BASE_DIRECTORY.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Secure Local Filesystem API", version="1.0.0")


class FileOperationPayload(BaseModel):
    from_path: str
    to: str

    @model_validator(mode="before")
    @classmethod
    def map_from_field(cls, values: Any) -> Any:
        if isinstance(values, dict) and "from" in values and "from_path" not in values:
            values = {**values, "from_path": values["from"]}
        return values


def error_response(message: str, response_status: int) -> JSONResponse:
    return JSONResponse(status_code=response_status, content={"error": {"message": message}})


def resolve_path(relative_path: str, *, allow_root: bool = True) -> Path:
    if not isinstance(relative_path, str) or (not allow_root and not relative_path):
        raise ValueError("A relative path is required.")

    candidate = Path(relative_path)
    if candidate.is_absolute() or relative_path.startswith(("/", "\\")):
        raise PermissionError

    resolved = (BASE_DIRECTORY / candidate).resolve()
    try:
        resolved.relative_to(BASE_DIRECTORY)
    except ValueError as exc:
        raise PermissionError from exc
    return resolved


def display_path(relative_path: str) -> str:
    return relative_path.replace("\\", "/")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response("Invalid request.", status.HTTP_400_BAD_REQUEST)


@app.get("/files", response_model=None)
def list_files(path: str = Query(default="")) -> list[dict[str, Any]] | JSONResponse:
    try:
        directory = resolve_path(path)
    except PermissionError:
        return error_response("Access denied: Path is outside the allowed directory.", status.HTTP_403_FORBIDDEN)
    except ValueError:
        return error_response("A relative path is required.", status.HTTP_400_BAD_REQUEST)

    if not directory.exists():
        return error_response(f"Not Found: The path '{display_path(path)}' does not exist.", status.HTTP_404_NOT_FOUND)
    if not directory.is_dir():
        return error_response(f"Not Found: The path '{display_path(path)}' is not a directory.", status.HTTP_404_NOT_FOUND)

    entries = []
    for entry in directory.iterdir():
        entries.append({
            "name": entry.name,
            "type": "directory" if entry.is_dir() else "file",
            "size": 0 if entry.is_dir() else entry.stat().st_size,
        })
    return sorted(entries, key=lambda item: (item["type"] != "directory", item["name"].lower(), item["name"]))


@app.get("/search", response_model=None)
def search_files(query: str = Query(..., min_length=1), path: str = Query(default="")) -> list[str] | JSONResponse:
    try:
        search_root = resolve_path(path)
    except PermissionError:
        return error_response("Access denied: Path is outside the allowed directory.", status.HTTP_403_FORBIDDEN)
    except ValueError:
        return error_response("A relative path is required.", status.HTTP_400_BAD_REQUEST)

    if not search_root.exists():
        return error_response(f"Not Found: The path '{display_path(path)}' does not exist.", status.HTTP_404_NOT_FOUND)
    if not search_root.is_dir():
        return error_response(f"Not Found: The path '{display_path(path)}' is not a directory.", status.HTTP_404_NOT_FOUND)

    matches = []
    for entry in search_root.rglob("*"):
        if entry.is_file() and query.lower() in entry.name.lower():
            matches.append(entry.relative_to(BASE_DIRECTORY).as_posix())
    return sorted(matches)


def perform_operation(source_text: str, destination_text: str, operation: str) -> JSONResponse:
    try:
        source = resolve_path(source_text, allow_root=False)
        destination = resolve_path(destination_text, allow_root=False)
    except PermissionError:
        return error_response("Access denied: Path is outside the allowed directory.", status.HTTP_403_FORBIDDEN)
    except ValueError:
        return error_response("A relative path is required.", status.HTTP_400_BAD_REQUEST)

    if not source.exists():
        return error_response(f"Not Found: The path '{display_path(source_text)}' does not exist.", status.HTTP_404_NOT_FOUND)
    if destination.exists():
        return error_response(f"Conflict: The destination '{display_path(destination_text)}' already exists.", status.HTTP_409_CONFLICT)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if operation == "copy":
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        verb = "Copied"
    else:
        shutil.move(str(source), str(destination))
        verb = "Moved"
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"{verb} successfully from '{display_path(source_text)}' to '{display_path(destination_text)}'"},
    )


@app.post("/files/copy", response_model=None)
def copy_file(payload: FileOperationPayload) -> JSONResponse | dict[str, str]:
    return perform_operation(payload.from_path, payload.to, "copy")


@app.post("/files/move", response_model=None)
def move_file(payload: FileOperationPayload) -> JSONResponse | dict[str, str]:
    return perform_operation(payload.from_path, payload.to, "move")


@app.delete("/files", response_model=None)
def delete_file(path: str = Query(..., min_length=1)) -> JSONResponse | dict[str, str]:
    try:
        target = resolve_path(path, allow_root=False)
    except PermissionError:
        return error_response("Access denied: Path is outside the allowed directory.", status.HTTP_403_FORBIDDEN)
    except ValueError:
        return error_response("A relative path is required.", status.HTTP_400_BAD_REQUEST)

    if not target.exists():
        return error_response(f"Not Found: The path '{display_path(path)}' does not exist.", status.HTTP_404_NOT_FOUND)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Deleted successfully: '{display_path(path)}'"},
    )
