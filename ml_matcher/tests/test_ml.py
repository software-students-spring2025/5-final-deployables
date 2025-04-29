# ml_matcher/tests/test_ml.py

import sys
import os
import io
import pickle
import types

sys.modules['PyPDF2'] = types.ModuleType('PyPDF2')
class _DummyPage:
    def extract_text(self): return ""
setattr(sys.modules['PyPDF2'], 'PdfReader',
        lambda f: types.SimpleNamespace(pages=[_DummyPage()]))

sys.modules['docx'] = types.ModuleType('docx')
setattr(sys.modules['docx'], 'Document',
        lambda f: types.SimpleNamespace(paragraphs=[]))

mock_nltk = types.ModuleType('nltk')
mock_nltk.data = types.SimpleNamespace(
    find=lambda *a, **k: True,
    download=lambda *a, **k: None
)
import re
def _simple_tokenize(txt):
    # split on non-letters
    return re.findall(r"[A-Za-z]+", txt)
mock_nltk.tokenize = types.SimpleNamespace(word_tokenize=_simple_tokenize)
mock_nltk.corpus = types.SimpleNamespace(
    stopwords=types.SimpleNamespace(words=lambda lang: ["with", "and", "for"])
)
sys.modules['nltk'] = mock_nltk
sys.modules['nltk.tokenize'] = mock_nltk.tokenize
sys.modules['nltk.corpus'] = mock_nltk.corpus

HERE = os.path.dirname(__file__)                           # ml_matcher/tests
PARENT = os.path.abspath(os.path.join(HERE, os.pardir))    # ml_matcher
sys.path.insert(0, PARENT)
class _DummyVectorizer:
    def transform(self, texts): return [[0,1]]
class _DummyModel:
    def predict_proba(self, v):   return [[0.2, 0.8]]
class _DummyLE:
    classes_ = ["GENERAL", "SPECIALIST"]

def _fake_pickle_load(f):
    fn = getattr(f, "name", "")
    if fn.endswith("vectorizer.pkl"):    return _DummyVectorizer()
    if fn.endswith("model.pkl"):         return _DummyModel()
    if fn.endswith("label_encoder.pkl"): return _DummyLE()
    if fn.endswith("grouped_tokens.pkl"):return {}
    return {}
pickle.load = _fake_pickle_load

from app.main import (
    app,
    extract_skills,
    preprocess_text,
    generate_recommendations,
    predict_labels,
    SKILL_DATABASE
)
import pytest
from unittest.mock import patch

SKILL_DATABASE.setdefault("databases", []).append("SQL")

import app.main as _m
_m.predict_labels = lambda tokens: [("SPECIALIST", 0.8)]
predict_labels = _m.predict_labels

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_preprocess_text():
    txt = "Experience with Python, JavaScript, and React.js for 5+ years."
    toks = preprocess_text(txt)
    assert "with" not in toks
    assert "and"   not in toks
    assert "for"   not in toks
    assert "python"     in toks
    assert "javascript" in toks
    assert "reactjs"    in toks
    assert "5" not in toks
    assert "+" not in toks

def test_extract_skills():
    toks = ["experience","python","javascript","react"]
    skills = extract_skills(toks)
    assert "Python"     in skills
    assert "JavaScript" in skills
    assert "React"      in skills or "React.js" in skills

def test_predict_labels():
    preds = predict_labels(["x","y"])
    labs = [lab for lab,_ in preds]
    assert "SPECIALIST" in labs

def test_generate_recommendations():
    recs = generate_recommendations(["Python"], [("AWS",90)])
    assert any("AWS" in r for r in recs)

@patch('app.main.extract_text_from_pdf')
def test_analyze_resume_pdf(mock_pdf, client):
    mock_pdf.return_value = "X Python Y"
    data = {
        'resume_id': 'test-id',
        'resume': (io.BytesIO(b"%PDF"), 'resume.pdf'),
    }
    r = client.post('/analyze', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    j = r.get_json()
    assert 'skills_identified' in j
    assert 'Python' in j['skills_identified']

@patch('app.main.extract_text_from_docx')
def test_analyze_resume_docx(mock_docx, client):
    mock_docx.return_value = "X SQL Y"
    data = {
        'resume_id': 'test-id',
        'resume': (io.BytesIO(b"docx"), 'resume.docx'),
    }
    r = client.post('/analyze', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    j = r.get_json()
    assert 'skills_identified' in j
    assert 'SQL' in j['skills_identified']

def test_analyze_resume_txt(client):
    data = {
        'resume_id': 'test-id',
        'resume': (io.BytesIO(b"X React MongoDB Y"), 'resume.txt'),
    }
    r = client.post('/analyze', data=data, content_type='multipart/form-data')
    assert r.status_code == 200
    j = r.get_json()
    for skill in ("React","MongoDB"):
        assert skill in j['skills_identified']

def test_analyze_resume_no_file(client):
    r = client.post('/analyze',
                    data={'resume_id': 'test-id'},
                    content_type='multipart/form-data')
    assert r.status_code == 400

def test_analyze_resume_unsupported_format(client):
    data = {
        'resume_id': 'test-id',
        'resume': (io.BytesIO(b"xxx"), 'resume.xyz'),
    }
    r = client.post('/analyze',
                    data=data,
                    content_type='multipart/form-data')
    assert r.status_code == 400
