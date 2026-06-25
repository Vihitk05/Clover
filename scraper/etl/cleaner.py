import logging
from typing import Dict, List

from scraper.etl.job_ingestion import JobListingIngestionPipeline

logger = logging.getLogger(__name__)


class DataCleaner:
    def __init__(self):
        self.pipeline = JobListingIngestionPipeline()

    def clean_text(self, text: str) -> str:
        return self.pipeline.clean_text(text)

    def parse_salary(self, salary_text: str) -> Dict:
        return self.pipeline.parse_salary(salary_text)

    def normalize_location(self, location: str) -> str:
        return self.pipeline.normalize_location(location)

    def extract_seniority(self, title: str, description: str = '') -> str:
        return self.pipeline.extract_seniority(title, description)

    def extract_sector(self, title: str, description: str) -> str:
        return self.pipeline.extract_sector(title, description)

    def extract_skills(self, text: str) -> List[str]:
        return self.pipeline.extract_skills(text)

    def ingest_job(self, job_data: dict, default_source: str = "unknown") -> Dict:
        return self.pipeline.ingest(job_data, default_source=default_source)
