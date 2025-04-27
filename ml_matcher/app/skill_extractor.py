# ml_matcher/app/skill_extractor.py
import re
import nltk
import logging
from datetime import datetime, timedelta
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('skill_extractor')

class SkillExtractor:
    def __init__(self, db_client):
        self.db_client = db_client
        self.db = self.db_client["resume_analyzer"]
        self.job_collection = self.db["job_postings"]
        self.skill_collection = self.db["job_skills"]
        
        # Make sure NLTK data is downloaded
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
        
        # Load base skill list from database (if exists) or use default
        self.load_base_skills()
    
    def load_base_skills(self):
        """Load base skill list from database or use default"""
        # Create a flattened list of skills from all categories
        all_skills = []
        skill_categories = self.skill_collection.find({"type": "category"})
        
        for category in skill_categories:
            all_skills.extend(category.get('skills', []))
        
        # If no skills found in database, use a default set
        if not all_skills:
            # Default categories and skills
            default_categories = [
                {
                    "type": "category",
                    "name": "programming_languages",
                    "display_name": "Programming Languages",
                    "skills": [
                        "Python", "JavaScript", "Java", "C++", "C#", "Ruby", "PHP", 
                        "Swift", "Go", "Kotlin", "TypeScript", "Rust", "Scala", "R"
                    ]
                },
                {
                    "type": "category",
                    "name": "web_technologies",
                    "display_name": "Web Technologies",
                    "skills": [
                        "HTML", "CSS", "React", "Angular", "Vue.js", "Node.js", "Express",
                        "Django", "Flask", "Spring Boot", "ASP.NET", "Ruby on Rails"
                    ]
                },
                {
                    "type": "category",
                    "name": "data_science",
                    "display_name": "Data Science & AI",
                    "skills": [
                        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
                        "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas",
                        "NumPy", "Data Mining", "Statistical Analysis", "Big Data",
                        "Data Visualization", "Tableau", "Power BI"
                    ]
                },
                {
                    "type": "category",
                    "name": "devops",
                    "display_name": "DevOps & Cloud",
                    "skills": [
                        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "CI/CD",
                        "Jenkins", "Git", "Linux", "Bash", "Terraform", "Ansible",
                        "Prometheus", "Grafana", "ELK Stack"
                    ]
                },
                {
                    "type": "category",
                    "name": "databases",
                    "display_name": "Databases",
                    "skills": [
                        "SQL", "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle",
                        "SQL Server", "Redis", "Elasticsearch", "DynamoDB", "Cassandra"
                    ]
                }
            ]
            
            # Save default categories to database
            for category in default_categories:
                self.skill_collection.update_one(
                    {"type": "category", "name": category["name"]},
                    {"$set": category},
                    upsert=True
                )
            
            # Flatten skills for detection
            for category in default_categories:
                all_skills.extend(category["skills"])
        
        # Create a set of all skills (lowercase for matching)
        self.all_skills = set(all_skills)
        self.all_skills_lower = {skill.lower(): skill for skill in all_skills}
        
        logger.info(f"Loaded {len(self.all_skills)} base skills for detection")
    
    def extract_skills_from_text(self, text):
        """Extract skills from job description text"""
        if not text:
            return []
        
        # Tokenize text
        tokens = nltk.word_tokenize(text.lower())
        
        # Find skills in tokens (single words)
        found_skills = set()
        for token in tokens:
            if token in self.all_skills_lower:
                found_skills.add(self.all_skills_lower[token])
        
        # Find multi-word skills
        for skill in self.all_skills:
            skill_lower = skill.lower()
            if " " in skill_lower and skill_lower in text.lower():
                found_skills.add(skill)
        
        # Check for programming languages with regex patterns
        lang_patterns = [
            r'\b(python|javascript|typescript|java|c\+\+|c#|ruby|go|php|swift|kotlin|rust|scala|r)\b'
        ]
        
        for pattern in lang_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if match in self.all_skills_lower:
                    found_skills.add(self.all_skills_lower[match])
        
        return list(found_skills)
    
    def process_job(self, job):
        """Process a job to extract skills"""
        if "description" not in job or not job["description"]:
            return
        
        # Extract skills from job description
        skills = self.extract_skills_from_text(job["description"])
        
        # Update job with extracted skills
        self.job_collection.update_one(
            {"_id": job["_id"]},
            {"$set": {"skills": skills}}
        )
    
    def process_all_jobs(self):
        """Process all jobs that haven't been processed yet"""
        # Get jobs without skills extracted
        unprocessed_jobs = self.job_collection.find(
            {"skills": {"$exists": False}}
        )
        
        count = 0
        for job in unprocessed_jobs:
            self.process_job(job)
            count += 1
        
        logger.info(f"Processed skills for {count} jobs")
    
    def update_skill_statistics(self, days=30):
        """Update skill statistics based on job data"""
        # Get recent jobs within the specified time period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_jobs = self.job_collection.find(
            {"scraped_date": {"$gte": cutoff_date}}
        )
        
        # Count skill occurrences
        skill_counter = Counter()
        job_count = 0
        
        for job in recent_jobs:
            skills = job.get("skills", [])
            for skill in skills:
                skill_counter[skill] += 1
            job_count += 1
        
        if job_count == 0:
            logger.warning("No recent jobs found for skill statistics update")
            return
        
        # Calculate demand percentage (normalize to 0-100)
        skill_demand = {}
        for skill, count in skill_counter.items():
            # Formula: (occurrences / total_jobs) * 100
            demand = (count / job_count) * 100
            # Cap at 100
            skill_demand[skill] = min(100, demand)
        
        # Save to database
        stats_doc = {
            "type": "statistics",
            "date": datetime.utcnow(),
            "period_days": days,
            "total_jobs": job_count,
            "skill_demand": skill_demand
        }
        
        self.skill_collection.update_one(
            {"type": "statistics"},
            {"$set": stats_doc},
            upsert=True
        )
        
        logger.info(f"Updated skill statistics based on {job_count} jobs")
        
        # Also update each skill category with demand scores
        self._update_skill_categories(skill_demand)
    
    def _update_skill_categories(self, skill_demand):
        """Update demand scores in skill categories"""
        categories = self.skill_collection.find({"type": "category"})
        
        for category in categories:
            skills = category.get("skills", [])
            updated_skills = []
            
            for skill in skills:
                demand = skill_demand.get(skill, 0)
                updated_skills.append({
                    "name": skill,
                    "demand": demand
                })
            
            # Sort by demand (highest first)
            updated_skills.sort(key=lambda x: x["demand"], reverse=True)
            
            # Update the category
            self.skill_collection.update_one(
                {"_id": category["_id"]},
                {"$set": {"skills_with_demand": updated_skills}}
            )
        
        logger.info("Updated skill categories with demand scores")
    
    def get_current_skill_demand(self):
        """Get the current skill demand stats"""
        stats = self.skill_collection.find_one({"type": "statistics"})
        if not stats:
            return {}
        
        return stats.get("skill_demand", {})