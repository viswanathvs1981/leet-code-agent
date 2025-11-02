import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as leetcode_app  # noqa: E402
from app import app as flask_app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_data():
    (
        problems,
        categories,
        patterns,
        tutorial,
        source,
        refreshed_at,
    ) = leetcode_app.initialise_data()
    leetcode_app.PROBLEMS = problems
    leetcode_app.CATEGORIES = categories
    leetcode_app.PATTERNS = patterns
    leetcode_app.TUTORIAL = tutorial
    leetcode_app.DATA_SOURCE = source
    leetcode_app.LAST_REFRESHED_AT = refreshed_at
    yield


def test_meta_endpoint():
    with flask_app.test_client() as client:
        response = client.get("/api/meta")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["source"].startswith("local dataset") or "leetcode-mcp-server" in payload["source"]
        assert payload["last_refreshed"] is not None


def test_categories_endpoint_has_content():
    with flask_app.test_client() as client:
        response = client.get("/api/categories")
        assert response.status_code == 200
        payload = response.get_json()
        assert "categories" in payload
        assert isinstance(payload["categories"], dict)
        assert payload["categories"]


def test_question_endpoint_returns_matches():
    with flask_app.test_client() as client:
        response = client.post(
            "/api/questions",
            data=json.dumps({"question": "dynamic programming practice"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert "answer" in payload
        assert payload["related_problems"], "Expected at least one related problem for dynamic programming"


def test_refresh_endpoint_updates_timestamp():
    with flask_app.test_client() as client:
        first_meta = client.get("/api/meta").get_json()
        response = client.post("/api/refresh")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "ok"
        updated_meta = client.get("/api/meta").get_json()
        assert updated_meta["last_refreshed"] >= first_meta["last_refreshed"]
