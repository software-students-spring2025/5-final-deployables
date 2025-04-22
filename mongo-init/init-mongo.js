// mongo-init/init-mongo.js
db = db.getSiblingDB('resume_analyzer');

// Create collections
db.createCollection('resumes');
db.createCollection('analyses');
db.createCollection('job_skills');

// Insert sample job skills data
db.job_skills.insertMany([
  {
    "category": "programming_languages",
    "skills": [
      {"name": "Python", "demand": 95},
      {"name": "JavaScript", "demand": 90},
      {"name": "Java", "demand": 85},
      {"name": "C++", "demand": 75},
      {"name": "Ruby", "demand": 65},
      {"name": "Go", "demand": 80},
      {"name": "PHP", "demand": 60},
      {"name": "Swift", "demand": 70},
      {"name": "TypeScript", "demand": 85},
      {"name": "C#", "demand": 75}
    ]
  },
  {
    "category": "web_technologies",
    "skills": [
      {"name": "React", "demand": 90},
      {"name": "Angular", "demand": 75},
      {"name": "Vue.js", "demand": 80},
      {"name": "Node.js", "demand": 85},
      {"name": "Django", "demand": 70},
      {"name": "Flask", "demand": 65},
      {"name": "Express.js", "demand": 75},
      {"name": "HTML", "demand": 80},
      {"name": "CSS", "demand": 80},
      {"name": "Bootstrap", "demand": 65}
    ]
  },
  {
    "category": "cloud_platforms",
    "skills": [
      {"name": "AWS", "demand": 90},
      {"name": "Azure", "demand": 85},
      {"name": "Google Cloud", "demand": 80},
      {"name": "Heroku", "demand": 65},
      {"name": "DigitalOcean", "demand": 70},
      {"name": "Kubernetes", "demand": 85},
      {"name": "Docker", "demand": 90}
    ]
  },
  {
    "category": "databases",
    "skills": [
      {"name": "MongoDB", "demand": 80},
      {"name": "PostgreSQL", "demand": 85},
      {"name": "MySQL", "demand": 80},
      {"name": "SQLite", "demand": 65},
      {"name": "Redis", "demand": 75},
      {"name": "Elasticsearch", "demand": 70}
    ]
  },
  {
    "category": "data_science",
    "skills": [
      {"name": "Machine Learning", "demand": 90},
      {"name": "Data Analysis", "demand": 85},
      {"name": "TensorFlow", "demand": 80},
      {"name": "PyTorch", "demand": 75},
      {"name": "Pandas", "demand": 80},
      {"name": "NumPy", "demand": 75},
      {"name": "Data Visualization", "demand": 70},
      {"name": "Scikit-learn", "demand": 75}
    ]
  }
]);

print("Mongo initialization complete");