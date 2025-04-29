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

from app.main import app

client = TestClient(app)

# Mock MongoDB client
@pytest.fixture
def mock_mongo(monkeypatch):
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_resume_collection = MagicMock()
    mock_analysis_collection = MagicMock()
    
    mock_client.resume_analyzer = mock_db
    mock_db.resumes = mock_resume_collection
    mock_db.analyses = mock_analysis_collection
    
    # Set up return values
    mock_analysis_collection.find_one.return_value = {
        "resume_id": "test-id",
        "match_score": 85.5,
        "skills_identified": ["Python", "JavaScript", "React"],
        "missing_skills": [("AWS", 90), ("Docker", 85)],
        "recommendations": ["Test recommendation"]
    }
    
    mock_resume_collection.find_one.return_value = {
        "id": "test-id",
        "name": "Test User",
        "email": "test@example.com"
    }
    
    mock_analysis_collection.find.return_value.sort.return_value.limit.return_value = [
        {"resume_id": "test-id-1", "match_score": 80},
        {"resume_id": "test-id-2", "match_score": 75}
    ]
    
    # Patch MongoClient
    monkeypatch.setattr("pymongo.MongoClient", lambda _: mock_client)
    
    return {
        "client": mock_client,
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
    # Mock the ML service response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "match_score": 85.5,
        "skills_identified": ["Python", "JavaScript", "React"],
        "missing_skills": [("AWS", 90), ("Docker", 85)],
        "recommendations": ["Test recommendation"]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    # Create test file
    test_file_content = b"This is a test resume content"
    
    # Make the request
    response = client.post(
        "/upload",
        files={"resume": ("test_resume.pdf", test_file_content, "application/pdf")},
        data={"name": "Test User", "email": "test@example.com"}
    )
    
    # Assert response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that MongoDB was called to insert data
    resume_collection = mock_mongo["resume_collection"]
    analysis_collection = mock_mongo["analysis_collection"]
    
    assert resume_collection.insert_one.call_count == 1
    assert analysis_collection.insert_one.call_count == 1

@patch("app.main.requests.post")
def test_upload_resume_ml_error(mock_post, mock_mongo):
    """Test error handling when ML service fails"""
    # Mock the ML service error
    mock_post.side_effect = Exception("ML service error")
    
    # Create test file
    test_file_content = b"This is a test resume content"
    
    # Make the request
    response = client.post(
        "/upload",
        files={"resume": ("test_resume.pdf", test_file_content, "application/pdf")},
        data={"name": "Test User", "email": "test@example.com"}
    )
    
    # Assert response
    assert response.status_code == 500
    assert "ML service error" in response.json()["detail"]

def test_get_results_success(mock_mongo):
    """Test getting results for a resume"""
    response = client.get("/results/test-id")
    
    # Assert response
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    # Check that MongoDB was called to find data
    analysis_collection = mock_mongo["analysis_collection"]
    resume_collection = mock_mongo["resume_collection"]
    
    analysis_collection.find_one.assert_called_once_with({"resume_id": "test-id"})
    resume_collection.find_one.assert_called_once_with({"id": "test-id"})

def test_get_results_not_found(mock_mongo):
    """Test getting results for a non-existent resume"""
    # Change the mock to return None
    mock_mongo["analysis_collection"].find_one.return_value = None
    
    response = client.get("/results/non-existent-id")
    
    # Assert response
    assert response.status_code == 404
    assert "Analysis not found" in response.json()["detail"]

def test_list_analyses(mock_mongo):
    """Test the API endpoint to list analyses"""
    response = client.get("/api/analyses")
    
    # Assert response
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["resume_id"] == "test-id-1"
    
    # Check that MongoDB was called correctly
    analysis_collection = mock_mongo["analysis_collection"]
    analysis_collection.find.assert_called_once()