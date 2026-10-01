import shutil

import pytest

from fastapi.testclient import TestClient

from app.main import BASE_DIRECTORY, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_test_entries():
    test_entries = ["a-directory", "z-file.txt", "test-source.txt", "test-destination.txt"]
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
