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

class IndeedSpider:
    def __init__(self):
        self.source_name = 'indeed'
        self.apify_token = config.APIFY_TOKEN
        self.client = ApifyClient(token=self.apify_token) if self.apify_token else None
        self.stats = {'jobs_found': 0, 'errors': 0}
    
    def scrape_all_jobs(self, search_queries: List[Dict] = None, target_count: int = 500) -> List[Dict]:
        if not self.client:
            logger.error("Apify token not configured")
            return []
        
        if search_queries is None:
            search_queries = [
                {"title": "software engineer", "location": "Ireland"},
                {"title": "data scientist", "location": "Ireland"},
                {"title": "python developer", "location": "Ireland"},
                {"title": "full stack developer", "location": "Ireland"},
                {"title": "devops engineer", "location": "Ireland"},
                {"title": "data analyst", "location": "Ireland"}
            ]
        
        all_jobs = []
        jobs_per_query = max(30, target_count // len(search_queries))
        
        for query in search_queries:
            if len(all_jobs) >= target_count:
                break
                
            try:
                run_input = {
                    "country": "ie",
                    "title": query.get("title"),
                    "location": query.get("location"),
                    "limit": min(jobs_per_query, 500),
                    "datePosted": "7"
                }
                
                logger.info(f"Scraping: {query['title']} in {query['location']}")
                actor_run = self.client.actor("TrtlecxAsNRbKl1na").call(run_input=run_input)
                
                dataset_id = actor_run['defaultDatasetId']
                for item in self.client.dataset(dataset_id).iterate_items():
                    if len(all_jobs) >= target_count:
                        break
                    processed = self._process_job_item(item, query)
                    if processed:
                        all_jobs.append(processed)
                        
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error: {e}")
                self.stats['errors'] += 1
        
        self.stats['jobs_found'] = len(all_jobs)
        return all_jobs
    
    def _process_job_item(self, item: Dict, query: Dict) -> Optional[Dict]:
        try:
            from scraper.etl.cleaner import DataCleaner
            cleaner = DataCleaner()
            
            job = {
                'source': self.source_name,
                'url': item.get('url', ''),
                'title': cleaner.clean_text(item.get('title', '')),
                'company': cleaner.clean_text(item.get('employer', {}).get('name', '')),
                'scraped_at': datetime.utcnow().isoformat(),
                'is_active': True
            }
            
            loc_data = item.get('location', {})
            job['location'] = loc_data.get('city', query.get('location', 'Ireland'))
            
            salary_data = item.get('baseSalary', {})
            if salary_data:
                min_sal = salary_data.get('min')
                max_sal = salary_data.get('max')
                if min_sal:
                    job['salary_min'] = min_sal
                    job['salary_max'] = max_sal if max_sal else min_sal
            
            desc_data = item.get('description', {})
            description = desc_data.get('text', '') or desc_data.get('html', '')
            import re
            description = re.sub(r'<[^>]+>', ' ', description)
            job['description_raw'] = cleaner.clean_text(description)
            
            indeed_skills = []
            for value in item.get('attributes', {}).values():
                if isinstance(value, str) and len(value) > 2:
                    indeed_skills.append(value)
            
            extracted = cleaner.extract_skills(description + ' ' + job['title'])
            job['skills_extracted'] = list(set(indeed_skills + extracted))
            
            title_lower = job['title'].lower()
            if any(w in title_lower for w in ['senior', 'lead']):
                job['seniority'] = 'Senior'
            elif any(w in title_lower for w in ['junior', 'entry', 'graduate']):
                job['seniority'] = 'Junior'
            elif any(w in title_lower for w in ['manager', 'director']):
                job['seniority'] = 'Lead'
            else:
                job['seniority'] = 'Mid'
            
            job['sector'] = cleaner.extract_sector(job['title'], description)
            job['posted_at'] = item.get('datePublished')
            
            return job
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return None