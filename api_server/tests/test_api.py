# api_server/tests/test_api.py
import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_database

client = TestClient(app)

# Mock MongoDB client
@pytest.fixture
def mock_mongo(monkeypatch):
    mock_client = MagicMock()
    mock_db = MagicMock()

    # Resume collection mock
    mock_resume_collection = MagicMock()
    mock_resume_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")
    mock_resume_collection.find_one.return_value = {
        "id": "test-id",
        "name": "Test User",
        "email": "test@example.com",
        "_id": "some_id"
    }

    # Analysis collection mock
    mock_analysis_collection = MagicMock()
    mock_analysis_collection.insert_one.return_value = MagicMock(inserted_id="fake-id")
    mock_analysis_collection.find_one.return_value = {
        "resume_id": "test-id",
        "match_score": 85.5,
        "skills_identified": ["Python", "JavaScript", "React"],
        "missing_skills": [("AWS", 90), ("Docker", 85)],
        "recommendations": ["Test recommendation"],
        "_id": "some_id"
    }

    # Make find().sort(...).limit(...) return a list of analyses, each with an _id
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor  # chaining .sort()
    mock_cursor.limit.return_value = [
        {"_id": "some_id_1", "resume_id": "test-id-1", "match_score": 80},
        {"_id": "some_id_2", "resume_id": "test-id-2", "match_score": 75}
    ]
    mock_analysis_collection.find.return_value = mock_cursor

    # Link the collections
    mock_db.resumes = mock_resume_collection
    mock_db.analyses = mock_analysis_collection

    # Override the MongoClient so get_database() returns our mock_db
    monkeypatch.setattr("pymongo.MongoClient", lambda _: mock_client)
    mock_client.__getitem__.return_value = mock_db

    app.dependency_overrides[get_database] = lambda: mock_db

    return {
        "client": mock_client,
        "db": mock_db,
        "resume_collection": mock_resume_collection,
        "analysis_collection": mock_analysis_collection
    }

def test_read_root(mock_mongo):
    """Test the root endpoint returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@patch("app.main.requests.post")
def test_upload_resume_success(mock_post, mock_mongo):
    """Test successful resume upload and analysis"""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "match_score": 85.5,
        "skills_identified": ["Python", "JavaScript", "React"],
        "missing_skills": [("AWS", 90), ("Docker", 85)],
        "recommendations": ["Test recommendation"]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    test_file_content = b"This is a test resume content"
    response = client.post(
        "/upload",
        files={"resume": ("test_resume.pdf", test_file_content, "application/pdf")},
        data={"name": "Test User", "email": "test@example.com"}
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    resume_collection = mock_mongo["resume_collection"]
    analysis_collection = mock_mongo["analysis_collection"]
    assert resume_collection.insert_one.call_count == 1
    assert analysis_collection.insert_one.call_count == 1

@patch("app.main.requests.post")
def test_upload_resume_ml_error(mock_post, mock_mongo):
    """Test error handling when ML service fails"""
    mock_post.side_effect = Exception("ML service error")

    test_file_content = b"This is a test resume content"
    response = client.post(
        "/upload",
        files={"resume": ("test_resume.pdf", test_file_content, "application/pdf")},
        data={"name": "Test User", "email": "test@example.com"}
    )

    assert response.status_code == 500
    assert "ML service error" in response.json()["detail"]

def test_get_results_success(mock_mongo):
    """Test getting results for a resume"""
    response = client.get("/results/test-id")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    analysis_collection = mock_mongo["analysis_collection"]
    resume_collection = mock_mongo["resume_collection"]
    analysis_collection.find_one.assert_called_once_with({"resume_id": "test-id"})
    resume_collection.find_one.assert_called_once_with({"id": "test-id"})

def test_get_results_not_found(mock_mongo):
    """Test getting results for a non-existent resume"""
    mock_mongo["analysis_collection"].find_one.return_value = None

    response = client.get("/results/non-existent-id")
    assert response.status_code == 404
    assert "Analysis not found" in response.json()["detail"]

def test_list_analyses(mock_mongo):
    """Test the API endpoint to list analyses"""
    response = client.get("/api/analyses")

    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) == 2
    assert json_data[0]["resume_id"] == "test-id-1"

    analysis_collection = mock_mongo["analysis_collection"]
    analysis_collection.find.assert_called_once()
