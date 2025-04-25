from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import nltk
from nltk.corpus import stopwords

# Download NLTK stopwords once (on first run)
nltk.download('stopwords')

app = Flask(__name__)

# Sample skill list
SKILLS_DB = {"python", "java", "javascript", "sql", "react", "node", "aws", "docker", "flask", "html", "css"}

def extract_text_from_pdf(path):
    with open(path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() or "" for page in reader.pages])

def extract_text_from_docx(path):
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])

def identify_skills(text):
    words = set(word.lower() for word in text.split())
    filtered = words - set(stopwords.words('english'))
    found = SKILLS_DB & filtered
    missing = SKILLS_DB - found
    return list(found), [(skill, 90) for skill in missing]  # 90 = fake confidence for now

def preprocess_text():
    pass

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    print("Extracted Text:", text[:500])
    uploaded_file = request.files.get('resume')
    if not uploaded_file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(uploaded_file.filename)
    ext = os.path.splitext(filename)[1].lower()
    save_path = os.path.join('/tmp', filename)
    uploaded_file.save(save_path)

    # Extract text
    if ext == ".pdf":
        text = extract_text_from_pdf(save_path)
    elif ext == ".docx":
        text = extract_text_from_docx(save_path)
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    skills_found, missing_skills = identify_skills(text)

    return jsonify({
        "message": "Resume processed successfully",
        "match_score": round(len(skills_found) / len(SKILLS_DB) * 100, 1),
        "skills_identified": skills_found,
        "missing_skills": missing_skills,
        "recommendations": ["Consider learning " + skill for skill, _ in missing_skills]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
