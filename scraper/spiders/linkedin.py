import logging
from typing import List, Dict, Optional
from datetime import datetime
import sys
import os
import time
import json
from apify_client import ApifyClient

from config.settings import config

logger = logging.getLogger(__name__)

class LinkedInSpider:
    """Spider for LinkedIn using Apify"""
    
    def __init__(self):
        self.source_name = 'linkedin'
        self.apify_token = config.APIFY_TOKEN
        self.client = ApifyClient(token=self.apify_token) if self.apify_token else None
        self.start_time = None
        self.stats = {
            'jobs_found': 0,
            'jobs_inserted': 0,
            'errors': 0
        }
    
    def scrape_all_jobs(self, search_urls: List[str] = None, target_count: int = 1000) -> List[Dict]:
        """
        Scrape jobs from LinkedIn using Apify
        
        Args:
            search_urls: List of LinkedIn job search URLs
            target_count: Number of jobs to scrape (minimum 10, maximum limited by LinkedIn)
        """
        if not self.client:
            logger.error("Apify token not configured. Please set APIFY_TOKEN in .env")
            return []
        
        if search_urls is None:
            # Default Irish job searches
            search_urls = [
                "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=Ireland&geoId=104738515&f_TPR=r604800",
                "https://www.linkedin.com/jobs/search/?keywords=data%20scientist&location=Ireland&geoId=104738515&f_TPR=r604800",
                "https://www.linkedin.com/jobs/search/?keywords=python%20developer&location=Ireland&geoId=104738515&f_TPR=r604800",
                "https://www.linkedin.com/jobs/search/?keywords=full%20stack&location=Ireland&geoId=104738515&f_TPR=r604800",
                "https://www.linkedin.com/jobs/search/?keywords=machine%20learning&location=Ireland&geoId=104738515&f_TPR=r604800"
            ]
        
        all_jobs = []
        self.start_time = datetime.utcnow()
        logger.info(f"Starting LinkedIn scraper with Apify")
        logger.info(f"Target: {target_count} jobs")
        logger.info(f"Search URLs: {search_urls}")
        
        try:
            # Prepare Actor input - only include splitCountry if splitByLocation is True
            run_input = {
                "urls": search_urls,
                "scrapeCompany": True,  # Get company details
                "count": min(target_count, 1000),  # Apify can get up to 1000 per run
                "splitByLocation": target_count > 1000,  # Enable location splitting for >1000 jobs
            }
            
            # Only add splitCountry if splitByLocation is True
            if target_count > 1000:
                run_input["splitCountry"] = "IE"  # Split by Irish cities
            
            logger.info(f"Running Apify Actor with input: {json.dumps(run_input, indent=2)}")
            
            # Run the Actor and wait for it to finish
            actor_run = self.client.actor("hKByXkMQaC5Qt9UMN").call(run_input=run_input)
            
            logger.info(f"Actor run completed with status: {actor_run.get('status')}")
            
            # Fetch and process results
            dataset_id = actor_run['defaultDatasetId']
            logger.info(f"Fetching results from dataset: {dataset_id}")
            
            # Iterate through items
            jobs_count = 0
            for item in self.client.dataset(dataset_id).iterate_items():
                if jobs_count >= target_count:
                    break
                    
                try:
                    processed_job = self.process_job_item(item)
                    if processed_job:
                        all_jobs.append(processed_job)
                        self.stats['jobs_found'] += 1
                        jobs_count += 1
                        
                        if jobs_count % 100 == 0:
                            logger.info(f"Processed {jobs_count} jobs so far...")
                            
                except Exception as e:
                    logger.error(f"Error processing job item: {e}")
                    self.stats['errors'] += 1
                    continue
            
            self.stats['jobs_inserted'] = len(all_jobs)
            
        except Exception as e:
            logger.error(f"Apify Actor error: {e}")
            import traceback
            traceback.print_exc()
            self.stats['errors'] += 1
        
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        logger.info(f"LinkedIn scraping completed. Duration: {duration:.2f}s")
        logger.info(f"Stats: {self.stats}")
        
        return all_jobs
    
    def process_job_item(self, item: Dict) -> Optional[Dict]:
        """Process a single job item from Apify output to match our schema"""
        try:
            # Extract and clean data
            job = {
                'source': self.source_name,
                'url': item.get('link', ''),
                'title': item.get('title', ''),
                'company': item.get('companyName', ''),
                'scraped_at': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            # Handle location
            location_raw = item.get('location', '')
            if location_raw:
                # Normalize location (e.g., "Dublin, County Dublin, Ireland" -> "Dublin")
                if ',' in location_raw:
                    location_raw = location_raw.split(',')[0].strip()
                job['location'] = location_raw
            
            # Handle salary
            salary_info = item.get('salaryInfo', [])
            if salary_info:
                if isinstance(salary_info, list) and len(salary_info) >= 2:
                    # Salary range
                    job['salary_raw'] = f"€{salary_info[0]} - €{salary_info[1]}"
                elif isinstance(salary_info, list) and len(salary_info) == 1:
                    # Single salary
                    job['salary_raw'] = f"€{salary_info[0]}"
                elif isinstance(salary_info, str):
                    job['salary_raw'] = salary_info
            
            # Handle description
            description = item.get('descriptionText', '')
            if not description:
                description = item.get('descriptionHtml', '')
                # Strip HTML tags if present
                import re
                description = re.sub(r'<[^>]+>', ' ', description)
            
            job['description_raw'] = description.strip()
            
            # Extract skills from description
            from scraper.etl.cleaner import DataCleaner
            cleaner = DataCleaner()
            
            # Extract skills from description
            skills = cleaner.extract_skills(description + ' ' + job['title'])
            job['skills_extracted'] = skills
            
            # Determine seniority
            seniority = item.get('seniorityLevel', '')
            if not seniority:
                seniority = cleaner.extract_seniority(job['title'], description)
            job['seniority'] = seniority
            
            # Determine sector
            sector = cleaner.extract_sector(job['title'], description)
            if not sector:
                industries = item.get('industries', '')
                if industries:
                    industries_lower = industries.lower()
                    if 'fintech' in industries_lower or 'finance' in industries_lower:
                        sector = 'Fintech'
                    elif 'healthcare' in industries_lower:
                        sector = 'Healthcare'
                    elif 'saas' in industries_lower or 'software' in industries_lower:
                        sector = 'SaaS'
                    elif 'consulting' in industries_lower:
                        sector = 'Consulting'
                    elif 'e-commerce' in industries_lower:
                        sector = 'E-commerce'
            job['sector'] = sector or 'Technology'
            
            # Handle posted date
            posted_at = item.get('postedAt')
            if posted_at:
                try:
                    job['posted_at'] = posted_at
                except:
                    pass
            
            # Handle salary parsing if raw salary exists
            if job.get('salary_raw'):
                salary_parsed = cleaner.parse_salary(job['salary_raw'])
                if salary_parsed.get('min'):
                    job['salary_min'] = salary_parsed['min']
                if salary_parsed.get('max'):
                    job['salary_max'] = salary_parsed['max']
            
            # Add additional LinkedIn-specific fields (useful for analytics)
            job['linkedin_metadata'] = {
                'company_linkedin_url': item.get('companyLinkedinUrl'),
                'company_logo': item.get('companyLogo'),
                'benefits': item.get('benefits', []),
                'employment_type': item.get('employmentType'),
                'workplace_types': item.get('workplaceTypes', []),
                'applicants_count': item.get('applicantsCount'),
                'job_function': item.get('jobFunction'),
                'industries': item.get('industries'),
                'company_description': item.get('companyDescription', '')[:500],  # Truncate
                'company_website': item.get('companyWebsite'),
                'company_employees_count': item.get('companyEmployeesCount'),
                'job_poster_name': item.get('jobPosterName'),
                'job_poster_title': item.get('jobPosterTitle')
            }
            
            return job
            
        except Exception as e:
            logger.error(f"Error processing LinkedIn job: {e}")
            return None
    
    def scrape_by_location_split(self, country: str = "IE", target_count: int = 1000) -> List[Dict]:
        """
        Scrape LinkedIn jobs with location splitting to bypass the 1000 job limit
        
        Args:
            country: Country code (default: IE for Ireland)
            target_count: Total jobs to scrape
        """
        # Common Irish cities for splitting
        irish_cities = [
            "Dublin", "Cork", "Galway", "Limerick", "Waterford", 
            "Kilkenny", "Wexford", "Sligo", "Donegal", "Kerry"
        ]
        
        all_jobs = []
        
        # Create search URLs for each city
        for city in irish_cities:
            if len(all_jobs) >= target_count:
                break
                
            search_url = f"https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location={city}%2C%20Ireland&geoId=104738515&f_TPR=r604800"
            
            logger.info(f"Scraping jobs for {city}...")
            jobs = self.scrape_all_jobs(search_urls=[search_url], target_count=target_count - len(all_jobs))
            all_jobs.extend(jobs)
            
            # Add delay between city searches
            time.sleep(2)
        
        return all_jobs