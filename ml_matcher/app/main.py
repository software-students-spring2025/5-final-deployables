# ml_matcher/app/main.py (update to use real data)
from flask import Flask, request, jsonify
import os
import PyPDF2
import docx
import nltk
import re
import pymongo
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from app.skill_extractor import SkillExtractor
from app.scrapers.scrape_scheduler import ScrapeScheduler

# Initialize Flask app
app = Flask(__name__)

# Connect to MongoDB
mongo_uri = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
mongo_client = pymongo.MongoClient(mongo_uri)

# Create skill extractor
skill_extractor = SkillExtractor(mongo_client)

# Start scheduler in background (commented out for testing)
# scrape_scheduler = ScrapeScheduler(mongo_uri)
# scheduler_thread = scrape_scheduler.start_scheduler_thread()

# Make sure NLTK data is downloaded
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

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
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Remove stopwords and non-alphanumeric tokens
    stop_words = set(stopwords.words('english'))
    tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
    
    return tokens

def extract_skills(tokens, text=None):
    """Extract skills from preprocessed text tokens"""
    # Use the skill extractor
    extracted_skills = []
    
    # First check tokens (single words)
    for token in tokens:
        if token in skill_extractor.all_skills_lower:
            extracted_skills.append(skill_extractor.all_skills_lower[token])
    
    # Also check the full text for multi-word skills
    if text:
        text_lower = text.lower()
        for skill in skill_extractor.all_skills:
            if " " in skill and skill.lower() in text_lower:
                extracted_skills.append(skill)
    
    return list(set(extracted_skills))  # Remove duplicates

def calculate_match_score(identified_skills):
    """Calculate match score based on identified skills and job market demand"""
    if not identified_skills:
        return 0
    
    # Get current skill demand from database
    skill_demand = skill_extractor.get_current_skill_demand()
    
    # If no demand data yet, use basic scoring
    if not skill_demand:
        return min(len(identified_skills) * 10, 100)  # Simple score based on number of skills
    
    # Calculate score based on demand for identified skills
    total_demand = 0
    skill_count = 0
    
    for skill in identified_skills:
        if skill in skill_demand:
            total_demand += skill_demand[skill]
            skill_count += 1
    
    # If no skills matched with demand data
    if skill_count == 0:
        return min(len(identified_skills) * 10, 100)  # Fall back to simple scoring
    
    # Normalize score to 0-100
    # Formula: Average demand of identified skills
    score = total_demand / skill_count
    
    return min(score, 100)  # Cap at 100

def identify_missing_skills(identified_skills):
    """Identify high-demand skills that are missing from the resume"""
    # Get current skill demand from database
    skill_demand = skill_extractor.get_current_skill_demand()
    
    # If no demand data yet, return empty list
    if not skill_demand:
        return []
    
    missing_skills = []
    
    # Look for high-demand skills that aren't in the identified skills
    for skill, demand in skill_demand.items():
        if skill not in identified_skills and demand >= 50:  # Only include medium to high-demand skills
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
    
    # Get skills from database for more tailored recommendations
    db = mongo_client["resume_analyzer"]
    job_collection = db["job_postings"]
    
    # Find recent jobs that match some of the person's skills
    if identified_skills:
        matching_jobs = job_collection.find({
            "skills": {"$in": identified_skills}
        }).sort("scraped_date", -1).limit(3)
        
        job_titles = [job.get("title", "") for job in matching_jobs]
        if job_titles:
            recommendations.append(f"Your skills align with positions like: {', '.join(job_titles)}.")
    
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
        identified_skills = extract_skills(tokens, text)
        
        # Calculate match score
        match_score = calculate_match_score(identified_skills)
        
        # Identify missing skills
        missing_skills = identify_missing_skills(identified_skills)
        
        # Generate recommendations
        recommendations = generate_recommendations(identified_skills, missing_skills)
        
        # Return analysis results
        return jsonify({
            "resume_id": resume_id,
            "match_score": match_score,
            "skills_identified": identified_skills,
            "missing_skills": missing_skills,
            "recommendations": recommendations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ml_matcher/app/main.py (add endpoint to trigger scraper)
@app.route('/run-scraper', methods=['POST'])
def run_scraper():
    """Run the job scraper manually"""
    try:
        # Initialize scraper
        scrape_scheduler = ScrapeScheduler(mongo_uri)
        
        # Run scrapers
        scrape_scheduler.run_scrapers()
        
        return jsonify({
            "success": True,
            "message": "Job scraping completed successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# For direct execution
if __name__ == '__main__':
    # Uncomment to start scraper on startup
    # scrape_scheduler = ScrapeScheduler(mongo_uri)
    # scheduler_thread = scrape_scheduler.start_scheduler_thread()
    
    app.run(host='0.0.0.0', port=5000, debug=True)