from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import requests
import uuid
import pymongo
from datetime import datetime

# Create the FastAPI app
app = FastAPI(title="Resume Analyzer API")

# Define base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# Explicitly define paths
static_path = os.path.join(APP_DIR, "static")
templates_path = os.path.join(APP_DIR, "templates")

# Create directories if they don't exist
os.makedirs(static_path, exist_ok=True)
os.makedirs(templates_path, exist_ok=True)

# Mount static files directory - with absolute path
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Set up templates with absolute path
templates = Jinja2Templates(directory=templates_path)

def get_database():
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
    mongo_client = pymongo.MongoClient(mongo_uri)
    db = mongo_client["resume_analyzer"]
    return db

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render the main page"""
    # For debugging, tell us what templates are available
    print(f"Templates directory: {templates_path}")
    print(f"Files in templates: {os.listdir(templates_path) if os.path.exists(templates_path) else 'Directory not found'}")
    
    # Return the index.html template
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_resume(
    request: Request,
    db=Depends(get_database),
    name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...)
):
    """Handle file upload and analyze"""
    try:
        # Generate a unique ID for this resume
        resume_id = str(uuid.uuid4())
        
        # Save the file temporarily
        file_location = f"/tmp/{resume_id}_{resume.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(await resume.read())
        
        # Prepare the file to be sent to the ML service
        with open(file_location, "rb") as f:
            files = {"resume": (resume.filename, f, resume.content_type)}
            form_data = {"resume_id": resume_id}
            
            # Send to ML service
            ml_service_url = os.environ.get("ML_API_URL", "http://ml:5000")
            response = requests.post(f"{ml_service_url}/analyze", files=files, data=form_data)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses
            
            # Get analysis results
            analysis_results = response.json()
        
        # Clean up the temporary file
        os.remove(file_location)
        
        # Store resume data in MongoDB
        # Initialize MongoDB client
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
        mongo_client = pymongo.MongoClient(mongo_uri)
        db = mongo_client["resume_analyzer"]
        
        # Store resume metadata
        db.resumes.insert_one({
            "id": resume_id,
            "name": name,
            "email": email,
            "filename": resume.filename,
            "upload_date": datetime.utcnow()
        })
        
        # Store analysis results
        db.analyses.insert_one({
            "resume_id": resume_id,
            "match_score": analysis_results.get("match_score", 0),
            "skills_identified": analysis_results.get("skills_identified", []),
            "missing_skills": analysis_results.get("missing_skills", []),
            "recommendations": analysis_results.get("recommendations", []),
            "analysis_date": datetime.utcnow()
        })
        
        # Redirect to results page
        return RedirectResponse(url=f"/results/{resume_id}", status_code=303)
    
    except requests.RequestException as e:
        # Handle ML service errors
        raise HTTPException(status_code=500, detail=f"ML service error: {str(e)}")
    except Exception as e:
        # Handle other errors
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")

@app.get("/results/{resume_id}", response_class=HTMLResponse)
async def get_results(request: Request, resume_id: str, db=Depends(get_database)):
    """Show analysis results"""
    try:
        # Get analysis results
        analysis = db.analyses.find_one({"resume_id": resume_id})
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Get resume metadata
        resume = db.resumes.find_one({"id": resume_id})
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Convert MongoDB ObjectId to string for JSON serialization
        analysis["_id"] = str(analysis["_id"])
        resume["_id"] = str(resume["_id"])
        
        # Render results template
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "resume_id": resume_id,
                "name": resume["name"],
                "results": analysis
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@app.get("/api/analyses")
async def list_analyses(db=Depends(get_database)):
    """API endpoint to list recent analyses"""
    try:
        # Get recent analyses
        analyses = list(db.analyses.find().sort("analysis_date", -1).limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for analysis in analyses:
            analysis["_id"] = str(analysis["_id"])
        
        return analyses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analyses: {str(e)}")