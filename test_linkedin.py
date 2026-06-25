#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.spiders.linkedin import LinkedInSpider
from config.settings import config
import json

def test_linkedin_scraper():
    """Test LinkedIn scraper"""
    print("="*60)
    print("Testing LinkedIn Scraper (Apify)")
    print("="*60)
    
    # Check if Apify token is configured
    if not config.APIFY_TOKEN:
        print("\n❌ APIFY_TOKEN not found in .env file!")
        print("Please add your Apify API token to .env:")
        print("APIFY_TOKEN=your_token_here")
        print("\nGet your token from: https://console.apify.com/account/integrations")
        return []
    
    scraper = LinkedInSpider()
    
    # Test with a single search URL and small count to avoid cost
    test_urls = [
        "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=Ireland&geoId=104738515&f_TPR=r604800"
    ]
    
    print("\n🕷️  Scraping 10 jobs from LinkedIn...")
    print(f"Using Apify token: {config.APIFY_TOKEN[:15]}...")
    jobs = scraper.scrape_all_jobs(search_urls=test_urls, target_count=10)
    
    print(f"\n✅ Found {len(jobs)} jobs")
    
    if jobs:
        print("\n📋 Sample Job Data (First 3 jobs):")
        print("-"*60)
        
        for idx, job in enumerate(jobs[:3], 1):
            print(f"\nJob {idx}:")
            print(f"  Title: {job.get('title', 'N/A')}")
            print(f"  Company: {job.get('company', 'N/A')}")
            print(f"  Location: {job.get('location', 'N/A')}")
            print(f"  Salary: {job.get('salary_raw', 'Not specified')}")
            print(f"  Seniority: {job.get('seniority', 'N/A')}")
            print(f"  Sector: {job.get('sector', 'N/A')}")
            print(f"  Skills: {job.get('skills_extracted', [])[:5]}")
            print(f"  URL: {job.get('url', 'N/A')}")
            
            # Show LinkedIn metadata
            if job.get('linkedin_metadata'):
                meta = job['linkedin_metadata']
                if meta.get('employment_type'):
                    print(f"  Employment Type: {meta.get('employment_type')}")
                if meta.get('workplace_types'):
                    print(f"  Workplace: {meta.get('workplace_types')}")
                if meta.get('applicants_count'):
                    print(f"  Applicants: {meta.get('applicants_count')}")
        
        # Save sample to file
        with open('sample_linkedin_jobs.json', 'w') as f:
            json.dump(jobs[:10], f, indent=2, default=str)
        print("\n📁 Sample jobs saved to sample_linkedin_jobs.json")
        print("\n✅ LinkedIn scraper is working!")
    else:
        print("\n⚠️  No jobs found. Check:")
        print("  1. Your Apify token is valid")
        print("  2. The search URLs are correct")
        print("  3. Your internet connection")
    
    return jobs

if __name__ == "__main__":
    jobs = test_linkedin_scraper()