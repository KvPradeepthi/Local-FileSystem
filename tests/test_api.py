import shutil

import pytest

from fastapi.testclient import TestClient

from app.main import BASE_DIRECTORY, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_entries():
    test_entries = [
        "a-directory",
        "z-file.txt",
        "test-source.txt",
        "test-destination.txt",
        "test-move-source.txt",
        "test-move-dest.txt",
        "test-delete.txt",
        "test-delete-dir",
    ]
    for name in test_entries:
        target = BASE_DIRECTORY / name
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)
    yield
    for name in test_entries:
        target = BASE_DIRECTORY / name
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)


def test_listing_is_sorted_and_reports_metadata(tmp_path):
    (BASE_DIRECTORY / "z-file.txt").write_text("data")
    (BASE_DIRECTORY / "a-directory").mkdir(exist_ok=True)

    response = client.get("/files")

    assert response.status_code == 200
    entries = response.json()
    assert [entry["type"] for entry in entries[:2]] == ["directory", "directory"]
    assert [entry["name"] for entry in entries[:2]] == ["a-directory", "documents"]
    assert [entry["name"] for entry in entries[2:]] == ["readme.txt", "z-file.txt"]
    assert entries[-1]["size"] == 4


def test_traversal_is_rejected():
    response = client.get("/files", params={"path": "../../etc"})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Access denied: Path is outside the allowed directory."


def test_copy_and_conflict():
    source = BASE_DIRECTORY / "test-source.txt"
    destination = BASE_DIRECTORY / "test-destination.txt"
    source.write_text("content")
    destination.unlink(missing_ok=True)

    response = client.post("/files/copy", json={"from": "test-source.txt", "to": "test-destination.txt"})
    assert response.status_code == 200
    assert source.exists() and destination.read_text() == "content"

    conflict = client.post("/files/copy", json={"from": "test-source.txt", "to": "test-destination.txt"})
    assert conflict.status_code == 409


def test_search_files():
    response = client.get("/search", params={"query": "report"})
    assert response.status_code == 200
    assert "documents/report.pdf" in response.json()

    # Search in non-existent directory returns 404
    not_found = client.get("/search", params={"query": "report", "path": "nonexistent_dir"})
    assert not_found.status_code == 404

    # Search with traversal returns 403
    traversal = client.get("/search", params={"query": "report", "path": "../"})
    assert traversal.status_code == 403


def test_move_and_conflict():
    source = BASE_DIRECTORY / "test-move-source.txt"
    dest = BASE_DIRECTORY / "test-move-dest.txt"
    source.write_text("move-content")
    dest.unlink(missing_ok=True)

    response = client.post("/files/move", json={"from": "test-move-source.txt", "to": "test-move-dest.txt"})
    assert response.status_code == 200
    assert not source.exists()
    assert dest.exists() and dest.read_text() == "move-content"

    # Moving to existing destination gives 409 conflict
    source.write_text("another-content")
    conflict = client.post("/files/move", json={"from": "test-move-source.txt", "to": "test-move-dest.txt"})
    assert conflict.status_code == 409


def test_delete_file_and_directory():
    target_file = BASE_DIRECTORY / "test-delete.txt"
    target_file.write_text("to-delete")
    response = client.delete("/files", params={"path": "test-delete.txt"})
    assert response.status_code == 200
    assert not target_file.exists()

    target_dir = BASE_DIRECTORY / "test-delete-dir"
    target_dir.mkdir(exist_ok=True)
    (target_dir / "nested.txt").write_text("nested")
    response = client.delete("/files", params={"path": "test-delete-dir"})
    assert response.status_code == 200
    assert not target_dir.exists()

    # Deleting nonexistent returns 404
    not_found = client.delete("/files", params={"path": "nonexistent.txt"})
    assert not_found.status_code == 404


def test_security_path_traversal_variants():
    traversal_paths = ["../", "../../", "../../../", "/etc/passwd", "\\Windows\\System32"]
    for path in traversal_paths:
        res = client.get("/files", params={"path": path})
        assert res.status_code == 403, f"Failed 403 check for {path}"
        assert res.json()["error"]["message"] == "Access denied: Path is outside the allowed directory."

