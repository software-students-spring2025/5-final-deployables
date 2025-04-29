# ml_matcher/tests/test_ml.py
import pytest
import sys
import os
import io
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, extract_skills, preprocess_text, generate_recommendations, predict_labels

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_preprocess_text():
    """Test text preprocessing"""
    text = "Experience with Python, JavaScript, and React.js for 5+ years."
    tokens = preprocess_text(text)
    
    # Check that stopwords are removed
    assert "with" not in tokens
    assert "and" not in tokens
    assert "for" not in tokens
    
    # Check that skills are preserved (but lowercase)
    assert "python" in tokens
    assert "javascript" in tokens
    assert "react" in tokens
    
    # Check that numbers and special chars are removed
    assert "5" not in tokens
    assert "+" not in tokens

def test_extract_skills():
    """Test skill extraction"""
    tokens = ["experience", "python", "javascript", "react"]
    skills = extract_skills(tokens)
    
    # Skills should be found and returned with proper casing
    assert "Python" in skills
    assert "JavaScript" in skills
    
    # React should be found despite case differences
    assert "React" in skills or "React.js" in skills

def test_predict_labels():
    """Test label predictions"""

    tokens = ["experience", "python", "javascript", "react"]
    predicted_labels = predict_labels(tokens)

    assert "SPECIALIST" in list(zip(*predicted_labels))[0]


def test_generate_recommendations():
    """Test recommendation generation"""
    identified_skills = ["Python", "JavaScript"]
    missing_skills = [("AWS", 90), ("Docker", 85)]
    
    recommendations = generate_recommendations(identified_skills, missing_skills)
    
    # Check that we have recommendations
    assert len(recommendations) > 0
    
    # Check that missing skills are mentioned
    assert any("AWS" in rec for rec in recommendations)
    assert any("Docker" in rec for rec in recommendations)

@patch('app.main.extract_text_from_pdf')
def test_analyze_resume_pdf(mock_extract_pdf, client):
    """Test PDF resume analysis"""
    # Mock the PDF extraction
    mock_extract_pdf.return_value = "Experience with Python and JavaScript"
    
    # Create a mock PDF file
    pdf_file = io.BytesIO(b"%PDF-1.5 mock pdf content")
    
    # Make the request
    response = client.post(
        '/analyze',
        data={
            'resume_id': 'test-id',
        },
        content_type='multipart/form-data',
        files={'resume': (io.BytesIO(pdf_file.read()), 'resume.pdf')}
    )
    
    # Check the response
    assert response.status_code == 200
    data = response.get_json()
    assert 'match_score' in data
    assert 'skills_identified' in data
    assert 'Python' in data['skills_identified']
    assert 'JavaScript' in data['skills_identified']

@patch('app.main.extract_text_from_docx')
def test_analyze_resume_docx(mock_extract_docx, client):
    """Test DOCX resume analysis"""
    # Mock the DOCX extraction
    mock_extract_docx.return_value = "Experience with Python and SQL"
    
    # Create a mock DOCX file
    docx_file = io.BytesIO(b"mock docx content")
    
    # Make the request
    response = client.post(
        '/analyze',
        data={
            'resume_id': 'test-id',
        },
        content_type='multipart/form-data',
        files={'resume': (io.BytesIO(docx_file.read()), 'resume.docx')}
    )
    
    # Check the response
    assert response.status_code == 200
    data = response.get_json()
    assert 'skills_identified' in data
    assert 'Python' in data['skills_identified']
    assert 'SQL' in data['skills_identified']

def test_analyze_resume_txt(client):
    """Test TXT resume analysis"""
    # Create a mock TXT file
    txt_content = "Experience with Python, React, and MongoDB"
    
    # Make the request
    response = client.post(
        '/analyze',
        data={
            'resume_id': 'test-id',
        },
        content_type='multipart/form-data',
        files={'resume': (io.BytesIO(txt_content.encode()), 'resume.txt')}
    )
    
    # Check the response
    assert response.status_code == 200
    data = response.get_json()
    assert 'skills_identified' in data
    assert 'Python' in data['skills_identified']
    assert 'React' in data['skills_identified']
    assert 'MongoDB' in data['skills_identified']

def test_analyze_resume_no_file(client):
    """Test error handling when no file is provided"""
    # Make the request without a file
    response = client.post(
        '/analyze',
        data={'resume_id': 'test-id'}
    )
    
    # Check the response
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'No resume file provided' in data['error']

def test_analyze_resume_unsupported_format(client):
    """Test error handling for unsupported file format"""
    # Create a mock file with unsupported extension
    mock_file = io.BytesIO(b"mock file content")
    
    # Make the request
    response = client.post(
        '/analyze',
        data={
            'resume_id': 'test-id',
        },
        content_type='multipart/form-data',
        files={'resume': (io.BytesIO(mock_file.read()), 'resume.xyz')}
    )
    
    # Check the response
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Unsupported file format' in data['error']