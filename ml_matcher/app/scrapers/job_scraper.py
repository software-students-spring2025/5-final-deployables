# ml_matcher/app/scrapers/job_scraper.py
import requests
from bs4 import BeautifulSoup
import time
import random
import logging
from datetime import datetime
from urllib.parse import urlencode

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('job_scraper')

class JobScraper:
    def __init__(self, db_client):
        self.db_client = db_client
        self.db = self.db_client["resume_analyzer"]
        self.job_collection = self.db["job_postings"]
        self.skill_collection = self.db["job_skills"]
        
        # Common headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def scrape_indeed(self, query, location, num_pages=5):
        """Scrape job postings from Indeed"""
        logger.info(f"Starting Indeed scraping for {query} in {location}")
        
        base_url = 'https://www.indeed.com/jobs'
        jobs = []
        
        for page in range(num_pages):
            # Create Indeed-compatible query parameters
            params = {
                'q': query,
                'l': location,
                'start': page * 10,  # Indeed uses 10 jobs per page
            }
            
            url = f"{base_url}?{urlencode(params)}"
            
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                job_cards = soup.find_all('div', class_='jobsearch-SerpJobCard')
                
                if not job_cards:
                    logger.warning(f"No job cards found on page {page+1}")
                    continue
                
                for card in job_cards:
                    try:
                        title_elem = card.find('h2', class_='title')
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        company = card.find('span', class_='company').text.strip() if card.find('span', class_='company') else "Unknown"
                        
                        # Get job URL
                        job_url = 'https://www.indeed.com' + title_elem.find('a')['href']
                        
                        # Get job description by visiting the job page
                        job_details = self._get_indeed_job_details(job_url)
                        
                        job = {
                            "title": title,
                            "company": company,
                            "location": location,
                            "description": job_details.get("description", ""),
                            "skills": job_details.get("skills", []),
                            "url": job_url,
                            "source": "indeed",
                            "query": query,
                            "scraped_date": datetime.utcnow()
                        }
                        
                        jobs.append(job)
                        
                        # Don't hammer the server
                        time.sleep(random.uniform(2, 5))
                        
                    except Exception as e:
                        logger.error(f"Error processing job card: {str(e)}")
                
                # Don't hammer the server between pages
                time.sleep(random.uniform(3, 7))
                
            except Exception as e:
                logger.error(f"Error scraping page {page+1}: {str(e)}")
        
        logger.info(f"Scraped {len(jobs)} jobs from Indeed")
        return jobs
    
    def _get_indeed_job_details(self, url):
        """Get detailed job information by visiting the job page"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract job description
            description_div = soup.find('div', id='jobDescriptionText')
            description = description_div.text.strip() if description_div else ""
            
            return {
                "description": description,
                "skills": []  # Skills will be extracted later
            }
            
        except Exception as e:
            logger.error(f"Error getting job details: {str(e)}")
            return {"description": "", "skills": []}
    
    def save_jobs_to_db(self, jobs):
        """Save scraped jobs to MongoDB"""
        if not jobs:
            logger.warning("No jobs to save")
            return 0
        
        # Check for duplicates by URL
        saved_count = 0
        for job in jobs:
            # Check if this job URL already exists
            existing = self.job_collection.find_one({"url": job["url"]})
            if not existing:
                self.job_collection.insert_one(job)
                saved_count += 1
        
        logger.info(f"Saved {saved_count} new jobs to database")
        return saved_count