```markdown
# Resume Analyzer Project

![API Server CI/CD](https://github.com/yourusername/resume-analyzer/actions/workflows/api_server.yml/badge.svg)
![ML Matcher CI/CD](https://github.com/yourusername/resume-analyzer/actions/workflows/ml_matcher.yml/badge.svg)

A comprehensive resume analysis system that uses machine learning to match resumes with job market requirements, providing personalized feedback and recommendations.

## Docker Images

- [Resume Analyzer API Server](https://hub.docker.com/r/yourusername/resume-analyzer-api)
- [Resume Analyzer ML Matcher](https://hub.docker.com/r/yourusername/resume-analyzer-ml)

## Team

- [Your Name](https://github.com/yourusername)
- [Team Member 2](https://github.com/teammember2)
- [Team Member 3](https://github.com/teammember3)

## Project Description

The Resume Analyzer is a comprehensive web application that helps job seekers improve their resumes by analyzing them against current job market trends. The system identifies skills present in the resume, highlights missing in-demand skills, and provides personalized recommendations for improvement.

### Key Features

- **Resume Parsing**: Extracts text and key information from PDF, DOCX, and TXT resumes
- **Skill Detection**: Identifies technical and soft skills present in the resume
- **Market Comparison**: Compares identified skills against current job market demands
- **Gap Analysis**: Highlights missing skills that are in high demand
- **Personalized Recommendations**: Provides tailored advice to improve resume effectiveness

### System Architecture

The project consists of three main components:

1. **API Server (FastAPI)**: Handles user interactions, file uploads, and results display
2. **ML Matcher Service (Flask)**: Performs resume parsing, skill extraction, and analysis
3. **MongoDB Database**: Stores resume data, analysis results, and job market information

## Installation and Setup

### Prerequisites

- Docker and Docker Compose
- Git

### Clone the Repository

```bash
git clone https://github.com/yourusername/resume-analyzer.git
cd resume-analyzer
```

### Environment Variables

Edit the `.env` file to set your specific configuration values.

### Running the Application

Start all services using Docker Compose:

```bash
docker-compose up -d
```

This will start the API server, ML matcher service, and MongoDB database.

### Accessing the Application

Once all services are running, you can access the application at:

- Web Interface: <http://localhost:8000>
- API Server Documentation: <http://localhost:8000/docs>
- ML Service API: <http://localhost:5000/analyze> (POST endpoint)

## Development and Testing

### Running Tests

To run tests for the API server:

```bash
cd api_server
pytest tests/ --cov=app
```

To run tests for the ML matcher:

```bash
cd ml_matcher
pytest tests/ --cov=app
```

### Uploading a Sample Resume

1. Visit <http://localhost:8000> in your browser
2. Enter your name and email
3. Upload a resume file (PDF, DOCX, or TXT format)
4. Click "Analyze Resume"
5. View the analysis results, including:
   - Overall match score
   - Identified skills
   - Missing in-demand skills
   - Personalized recommendations

## API Documentation

### API Server Endpoints

- `GET /`: Main web interface
- `POST /upload`: Upload and analyze a resume
- `GET /results/{resume_id}`: View analysis results for a specific resume
- `GET /api/analyses`: List recent analyses (JSON)

### ML Service Endpoints

- `POST /analyze`: Analyze a resume file

## CI/CD Pipeline

The project uses GitHub Actions for CI/CD:

- Automatically builds and tests on push or pull request to main branch
- Pushes Docker images to Docker Hub
- Deploys to Digital Ocean

### Required GitHub Secrets

For CI/CD to work, set the following GitHub Secrets:

- `DOCKER_USERNAME`: Docker Hub username
- `DOCKER_PASSWORD`: Docker Hub password
- `DIGITALOCEAN_HOST`: Digital Ocean droplet IP
- `DIGITALOCEAN_USERNAME`: SSH username
- `DIGITALOCEAN_SSHKEY`: SSH private key

## MongoDB Data Structure

The MongoDB database contains three collections:

- `resumes`: Stores information about uploaded resumes
- `analyses`: Stores analysis results
- `job_skills`: Stores job market data including skill demand levels

```
