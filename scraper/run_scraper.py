#!/usr/bin/env python
"""
Clover job ingestion pipeline.
Default mode: single run
Daemon mode: every 6 hours
"""

import hashlib
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import List, Tuple

from sqlalchemy.orm import Session

# Support running via `python scraper/run_scraper.py` by adding project root to sys.path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import config
from database.connections import db_manager
from scraper.etl.cleaner import DataCleaner
from scraper.etl.embedder import JobEmbedder
from scraper.models import Job, ScraperRun
from scraper.spiders.irishjobs import IrishJobsDirectSpider
from scraper.spiders.jobsie import JobsIEDirectSpider
from scraper.spiders.linkedin import LinkedInSpider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def utc_now_naive() -> datetime:
    """Return a UTC timestamp without tzinfo for existing naive DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def save_job(job_data: dict, session: Session) -> Job | None:
    """Save one normalized job with deduplication; returns saved row if inserted."""
    try:
        cleaner = DataCleaner()
        normalized = cleaner.ingest_job(job_data, default_source=job_data.get("source", "unknown"))
        title = normalized["title"]
        company = normalized["company"]
        location_raw = normalized["location"]
        description = normalized["description_raw"]

        if not title:
            logger.warning("Skipping job without a title from source=%s", normalized["source"])
            return None

        source_hash = hashlib.sha256(f"{title}|{company}|{location_raw}".encode()).hexdigest()
        existing = session.query(Job).filter_by(source_hash=source_hash).first()
        if existing:
            return None

        job = Job(
            id=str(uuid.uuid4()),
            source_hash=source_hash,
            title=title,
            company=company,
            location=location_raw,
            salary_min=normalized["salary_min"],
            salary_max=normalized["salary_max"],
            seniority=normalized["seniority"],
            sector=normalized["sector"],
            description_raw=description,
            skills_extracted=normalized["skills_extracted"],
            source=normalized["source"],
            url=normalized["url"],
            posted_at=normalized["posted_at"],
            is_active=True,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    except Exception as exc:
        logger.error(f"Error saving job: {exc}")
        session.rollback()
        return None


def _run_source(source: str, scrape_fn) -> Tuple[int, int, int]:
    session = db_manager.get_session()
    run = ScraperRun(
        id=str(uuid.uuid4()),
        source=source,
        status="running",
        started_at=utc_now_naive(),
    )
    session.add(run)
    session.commit()

    inserted_rows: List[Job] = []
    duplicates = 0
    jobs = []
    try:
        jobs = scrape_fn()
        for job in jobs:
            saved = save_job(job, session)
            if saved is None:
                duplicates += 1
            else:
                inserted_rows.append(saved)

        if inserted_rows:
            embedder = JobEmbedder(persist_directory=config.CHROMA_DB_PATH)
            embedder.embed_jobs(
                [
                    {
                        "id": row.id,
                        "title": row.title,
                        "company": row.company,
                        "location": row.location,
                        "seniority": row.seniority,
                        "skills_extracted": row.skills_extracted or [],
                        "salary_min": row.salary_min,
                        "salary_max": row.salary_max,
                        "source": row.source,
                        "description_raw": row.description_raw,
                    }
                    for row in inserted_rows
                ]
            )

        run.finished_at = utc_now_naive()
        run.jobs_found = len(jobs)
        run.jobs_inserted = len(inserted_rows)
        run.duplicates_skipped = duplicates
        run.status = "success" if len(inserted_rows) > 0 else "failed"
        session.add(run)
        session.commit()
        return len(jobs), len(inserted_rows), duplicates
    except Exception as exc:
        run.finished_at = utc_now_naive()
        run.status = "failed"
        session.add(run)
        session.commit()
        logger.error(f"{source} scrape failed: {exc}")
        return len(jobs), len(inserted_rows), duplicates
    finally:
        session.close()


def run_jobsie_scraper() -> Tuple[int, int, int]:
    spider = JobsIEDirectSpider()
    return _run_source("jobs.ie", lambda: spider.scrape_all_pages(max_pages=config.MAX_PAGES))


def run_irishjobs_scraper() -> Tuple[int, int, int]:
    spider = IrishJobsDirectSpider()
    return _run_source("irishjobs.ie", lambda: spider.scrape_all_pages(max_pages=config.MAX_PAGES))


def run_linkedin_scraper(target_count: int = 500) -> Tuple[int, int, int]:
    if not config.APIFY_TOKEN:
        logger.warning("APIFY_TOKEN not configured. Skipping LinkedIn source.")
        return 0, 0, 0

    spider = LinkedInSpider()
    urls = [
        "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&location=Ireland&geoId=104738515&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=data%20scientist&location=Ireland&geoId=104738515&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=python%20developer&location=Ireland&geoId=104738515&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=machine%20learning&location=Ireland&geoId=104738515&f_TPR=r604800",
        "https://www.linkedin.com/jobs/search/?keywords=full%20stack&location=Ireland&geoId=104738515&f_TPR=r604800",
    ]
    return _run_source("linkedin", lambda: spider.scrape_all_jobs(search_urls=urls, target_count=target_count))


def run_all_scrapers() -> int:
    logger.info("=" * 60)
    logger.info("Clover Multi-source Job Ingestion")
    logger.info("Sources: Jobs.ie, IrishJobs.ie, LinkedIn Ireland")
    logger.info("=" * 60)
    if not db_manager.init_db():
        logger.error("Database initialization failed")
        return 0

    started_at = utc_now_naive()
    jobsie_found, jobsie_inserted, _ = run_jobsie_scraper()
    time.sleep(2)
    irish_found, irish_inserted, _ = run_irishjobs_scraper()
    time.sleep(2)
    li_found, li_inserted, _ = run_linkedin_scraper(target_count=500)

    total_inserted = jobsie_inserted + irish_inserted + li_inserted
    duration = (utc_now_naive() - started_at).total_seconds()
    logger.info("=" * 60)
    logger.info("FINAL INGESTION SUMMARY")
    logger.info(f"Jobs.ie: found={jobsie_found} inserted={jobsie_inserted}")
    logger.info(f"IrishJobs.ie: found={irish_found} inserted={irish_inserted}")
    logger.info(f"LinkedIn: found={li_found} inserted={li_inserted}")
    logger.info(f"Total inserted={total_inserted} in {duration:.2f}s")
    logger.info("=" * 60)
    return total_inserted


def run_scheduler(interval_hours: int = 6):
    logger.info(f"Starting daemon mode with {interval_hours} hour interval")
    while True:
        try:
            run_all_scrapers()
        except Exception as exc:
            logger.error(f"Scheduled run failed: {exc}")
        logger.info(f"Sleeping for {interval_hours} hours...")
        time.sleep(interval_hours * 3600)


if __name__ == "__main__":
    mode = os.getenv("CLOVER_SCRAPER_MODE", "once").strip().lower()
    if mode == "daemon":
        run_scheduler(interval_hours=6)
    else:
        run_all_scrapers()
