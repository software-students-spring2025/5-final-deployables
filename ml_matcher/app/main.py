# ml_matcher/app/main.py
from flask import Flask, request, jsonify
import os
import PyPDF2
import docx
import nltk
import re
import pickle

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Initialize Flask app
app = Flask(__name__)

# Make sure NLTK data is downloaded (this is needed for tokenization and stopwords)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Skill database - in a real application, this would come from MongoDB
# This is a simplified version for development
SKILL_DATABASE = {
    "programming_languages": ["Python", "JavaScript", "Java", "C++", "Ruby", "Go", "PHP", "Swift", "TypeScript", "C#"],
    "web_technologies": ["React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "Express.js", "HTML", "CSS", "Bootstrap"],
    "cloud_platforms": ["AWS", "Azure", "Google Cloud", "Heroku", "DigitalOcean", "Kubernetes", "Docker"],
    "databases": ["MongoDB", "PostgreSQL", "MySQL", "SQLite", "Redis", "Elasticsearch"],
    "data_science": ["Machine Learning", "Data Analysis", "TensorFlow", "PyTorch", "Pandas", "NumPy", "Data Visualization", "Scikit-learn"]
}

# Job market demand - simplified version (1-100 scale)
SKILL_DEMAND = {
    "Python": 95, "JavaScript": 90, "Java": 85, "React": 90, "Angular": 75, 
    "AWS": 90, "Docker": 90, "MongoDB": 80, "PostgreSQL": 85, "Machine Learning": 90
}

with open('./model/model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('./model/vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)
with open('./model/label_encoder.pkl', 'rb') as f:
    label_encoder = pickle.load(f)
with open('./model/grouped_tokens.pkl', 'rb') as f:
    grouped_tokens = pickle.load(f)

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(docx_file):
    """Extract text from a DOCX file"""
    doc = docx.Document(docx_file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def preprocess_text(text):
    """Preprocess text for skill extraction"""
    # Convert to lowercase
    text = text.lower()

    # keep only letters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Remove stopwords and non-alphanumeric tokens
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
    
    return tokens

def extract_skills(tokens):
    """Extract skills from preprocessed text tokens"""
    # Flatten the skills database for easier lookup
    all_skills = []
    skill_lookup = {}  # Maps lowercase skill to proper case
    
    for category, skills in SKILL_DATABASE.items():
        for skill in skills:
            all_skills.append(skill.lower())
            skill_lookup[skill.lower()] = skill
    
    # Extract skills from tokens (look for single tokens and bigrams)
    extracted_skills = set()
    
    # Single token skills
    for token in tokens:
        if token in all_skills:
            extracted_skills.add(skill_lookup[token])
    
    # Bigram skills (for multi-word skills like "Machine Learning")
    bigrams = [tokens[i] + " " + tokens[i+1] for i in range(len(tokens)-1)]
    for bigram in bigrams:
        if bigram in all_skills:
            extracted_skills.add(skill_lookup[bigram])
    
    return list(extracted_skills)

def predict_labels(tokens):
    """Vectorizes the tokenized resume and runs it through the Random Forest Classifier and returns a list of the top 3 IT categories"""
    processed_text = ' '.join(tokens)
    text_vector = vectorizer.transform([processed_text])

    predicted_label_encoded = model.predict_proba(text_vector)[0]
    job_probs = list(zip(label_encoder.classes_), predicted_label_encoded)

    job_probs_sorted = sorted(job_probs, key=lambda x: x[1], reverse=True)
    return job_probs_sorted[0:3]

def calculate_match_score(identified_skills):
    """Calculate match score based on identified skills"""
    if not identified_skills:
        return 0
    
    # Calculate score based on demand for identified skills
    total_demand = 0
    for skill in identified_skills:
        if skill in SKILL_DEMAND:
            total_demand += SKILL_DEMAND[skill]
    
    # Normalize score to 0-100
    max_possible = 100 * min(len(identified_skills), 10)  # Cap at 10 skills for normalization
    if max_possible == 0:
        return 0
    
    score = (total_demand / max_possible) * 100
    return min(score, 100)  # Cap at 100

def identify_missing_skills(identified_skills):
    """Identify high-demand skills that are missing from the resume"""
    missing_skills = []
    
    # Look for high-demand skills that aren't in the identified skills
    for skill, demand in SKILL_DEMAND.items():
        if skill not in identified_skills and demand >= 75:  # Only include high-demand skills
            missing_skills.append((skill, demand))
    
    # Sort by demand (highest first) and limit to top 5
    missing_skills.sort(key=lambda x: x[1], reverse=True)
    return missing_skills[:5]

def generate_recommendations(identified_skills, missing_skills):
    """Generate personalized recommendations based on skills analysis"""
    recommendations = []
    
    # If few skills identified, recommend adding more skills
    if len(identified_skills) < 5:
        recommendations.append("Consider adding more specific technical skills to your resume.")
    
    # Recommendations based on missing high-demand skills
    if missing_skills:
        skills_str = ", ".join([skill for skill, _ in missing_skills[:3]])
        recommendations.append(f"Consider gaining experience with in-demand skills like {skills_str}.")
    
    # Add generic recommendations
    recommendations.append("Quantify your achievements with metrics and specific outcomes.")
    recommendations.append("Tailor your resume to match the specific job descriptions you're applying for.")
    
    return recommendations

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Analyze a resume file"""
    # Check if resume file is included
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400
    
    resume_file = request.files['resume']
    resume_id = request.form.get('resume_id', 'unknown')
    
    # Check file extension
    filename = resume_file.filename
    if not filename:
        return jsonify({"error": "Empty filename"}), 400
    
    # Extract text based on file type
    try:
        if filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf(resume_file)
        elif filename.lower().endswith('.docx'):
            text = extract_text_from_docx(resume_file)
        elif filename.lower().endswith('.txt'):
            text = resume_file.read().decode('utf-8')
        else:
            return jsonify({"error": "Unsupported file format. Please upload PDF, DOCX, or TXT"}), 400
        
        # Process text to extract skills
        tokens = preprocess_text(text)
        identified_skills = extract_skills(tokens)

        predicted_labels = predict_labels(tokens)
        
        # Calculate match score
        match_score = calculate_match_score(identified_skills)
        
        # Identify missing skills
        missing_skills = identify_missing_skills(identified_skills)
        
        # Generate recommendations
        recommendations = generate_recommendations(identified_skills, missing_skills)
        
        # Return analysis results
        return jsonify({
            "resume_id": resume_id,
            "predicted_labels": predicted_labels,
            "match_score": match_score,
            "skills_identified": identified_skills,
            "missing_skills": missing_skills,
            "recommendations": recommendations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# For direct execution
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
