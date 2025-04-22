from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import requests
import uuid
from datetime import datetime

# Create the FastAPI app
app = FastAPI(title="Resume Analyzer API")

# Explicitly define paths
static_path = os.path.join(os.path.dirname(__file__), "static")
templates_path = os.path.join(os.path.dirname(__file__), "templates")

# Create directories if they don't exist
os.makedirs(static_path, exist_ok=True)
os.makedirs(templates_path, exist_ok=True)

# Mount static files directory - with absolute path
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Set up templates with absolute path
templates = Jinja2Templates(directory=templates_path)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render the main page"""
    # For debugging, tell us what templates are available
    print(f"Templates directory: {templates_path}")
    print(f"Files in templates: {os.listdir(templates_path) if os.path.exists(templates_path) else 'Directory not found'}")
    
    # Create a simple HTML response instead of using template
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resume Analyzer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            h1 { color: #4a6fa5; }
            form { margin-top: 20px; }
            label { display: block; margin-bottom: 5px; }
            input { margin-bottom: 15px; padding: 5px; }
            button { background-color: #4a6fa5; color: white; padding: 10px 15px; 
                    border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>Resume Analyzer</h1>
        <p>Upload your resume for analysis</p>
        
        <form action="/upload" method="post" enctype="multipart/form-data">
            <div>
                <label for="name">Your Name:</label>
                <input type="text" id="name" name="name" required>
            </div>
            <div>
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" required>
            </div>
            <div>
                <label for="resume">Upload Resume:</label>
                <input type="file" id="resume" name="resume" accept=".pdf,.docx,.txt" required>
            </div>
            <button type="submit">Analyze Resume</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/upload")
async def upload_resume(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...)
):
    """Handle file upload and analyze"""
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Analysis Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            h1 {{ color: #4a6fa5; }}
            .result {{ margin-top: 20px; padding: 10px; background-color: #f5f5f5; }}
        </style>
    </head>
    <body>
        <h1>Analysis Results</h1>
        <div class="result">
            <p>Name: {name}</p>
            <p>Email: {email}</p>
            <p>File: {resume.filename}</p>
            <p>This is a test response. The ML service integration will be added next.</p>
        </div>
        <a href="/">Back to Upload</a>
    </body>
    </html>
    """)