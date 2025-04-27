# ml_matcher/app/scrapers/scrape_scheduler.py
import time
import threading
import schedule
import pymongo
import logging
from datetime import datetime
from app.scrapers.job_scraper import JobScraper
from app.skill_extractor import SkillExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('scrape_scheduler')

class ScrapeScheduler:
    def __init__(self, mongo_uri="mongodb://mongo:27017"):
        self.mongo_client = pymongo.MongoClient(mongo_uri)
        self.scraper = JobScraper(self.mongo_client)
        self.skill_extractor = SkillExtractor(self.mongo_client)
        
        # Tech job search terms - customize based on your focus
        self.search_queries = [
            "software engineer",
            "data scientist",
            "machine learning",
            "web developer",
            "devops",
            "product manager",
            "full stack developer"
        ]
        
        # Locations to search in
        self.locations = [
            "Remote",
            "New York, NY",
            "San Francisco, CA",
            "Seattle, WA",
            "Austin, TX",
            "Boston, MA"
        ]
    
    def run_scrapers(self):
        """Run all scrapers for each query and location"""
        logger.info("Starting scheduled job scraping")
        total_jobs = 0
        
        for query in self.search_queries:
            for location in self.locations:
                # Scrape Indeed
                jobs = self.scraper.scrape_indeed(query, location, num_pages=2)
                saved = self.scraper.save_jobs_to_db(jobs)
                total_jobs += saved
                
                # Add more scrapers here when implemented
                # e.g., jobs_linkedin = self.scraper.scrape_linkedin(...)
        
        logger.info(f"Completed scraping run. Added {total_jobs} new jobs.")
        
        # After scraping, update skill statistics
        if total_jobs > 0:
            self.skill_extractor.process_all_jobs()
            self.skill_extractor.update_skill_statistics()
    
    def schedule_jobs(self):
        """Schedule periodic scraping"""
        # Run once a day at 2:00 AM
        schedule.every().day.at("02:00").do(self.run_scrapers)
        
        # For testing: Also run immediately when started
        self.run_scrapers()
        
        logger.info("Scraper scheduled. Will run daily at 2:00 AM.")
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def start_scheduler_thread(self):
        """Start the scheduler in a background thread"""
        scheduler_thread = threading.Thread(target=self.schedule_jobs)
        scheduler_thread.daemon = True  # Thread will exit when main program exits
        scheduler_thread.start()
        logger.info("Scheduler thread started")
        return scheduler_thread