import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock
from typing import Callable, Dict, Optional

from sqlalchemy.orm import Session

from config.settings import config
from scraper.models import ScraperRun
from scraper.run_scraper import (
    run_all_scrapers,
    run_irishjobs_scraper,
    run_jobsie_scraper,
    run_linkedin_scraper,
)

logger = logging.getLogger(__name__)


ScrapeCallable = Callable[[], tuple[int, int, int]]


def _make_registry(target_count: Optional[int] = None) -> Dict[str, ScrapeCallable]:
    return {
        "jobsie": run_jobsie_scraper,
        "irishjobs": run_irishjobs_scraper,
        "linkedin": lambda: run_linkedin_scraper(target_count=target_count or 500),
        "all": lambda: (0, run_all_scrapers(), 0),
    }


class ScraperTaskManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="clover-scraper")
        self.lock = Lock()
        self.tasks: Dict[str, Dict] = {}

    def _set_task(self, task_id: str, patch: Dict):
        with self.lock:
            if task_id not in self.tasks:
                self.tasks[task_id] = {}
            self.tasks[task_id].update(patch)

    def get_task(self, task_id: str) -> Optional[Dict]:
        with self.lock:
            return dict(self.tasks[task_id]) if task_id in self.tasks else None

    def _execute(
        self,
        task_id: str,
        provider: str,
        retries: int,
        target_count: Optional[int],
    ) -> None:
        self._set_task(
            task_id,
            {
                "status": "running",
                "started_at": datetime.utcnow(),
                "attempts": 0,
            },
        )
        registry = _make_registry(target_count=target_count)
        runner = registry[provider]

        last_error = None
        for attempt in range(retries + 1):
            self._set_task(task_id, {"attempts": attempt + 1})
            try:
                found, inserted, duplicates = runner()
                self._set_task(
                    task_id,
                    {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                        "result": {
                            "jobs_found": found,
                            "jobs_inserted": inserted,
                            "duplicates_skipped": duplicates,
                        },
                    },
                )
                return
            except Exception as exc:  # pragma: no cover - defensive path
                last_error = str(exc)
                logger.exception("Scraper task failed: provider=%s attempt=%s", provider, attempt + 1)
                if attempt < retries:
                    time.sleep(min(2 ** attempt, 20))
        self._set_task(
            task_id,
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error": {"message": last_error or "unknown error"},
            },
        )

    def submit(
        self,
        provider: str,
        retries: int,
        target_count: Optional[int],
    ) -> Dict:
        task_id = str(uuid.uuid4())
        accepted_at = datetime.utcnow()
        self._set_task(
            task_id,
            {
                "task_id": task_id,
                "provider": provider,
                "status": "queued",
                "accepted_at": accepted_at,
            },
        )
        self.executor.submit(self._execute, task_id, provider, retries, target_count)
        return self.get_task(task_id) or {}

    def run_sync(
        self,
        provider: str,
        retries: int,
        target_count: Optional[int],
    ) -> Dict:
        task_id = str(uuid.uuid4())
        accepted_at = datetime.utcnow()
        self._set_task(
            task_id,
            {
                "task_id": task_id,
                "provider": provider,
                "status": "queued",
                "accepted_at": accepted_at,
            },
        )
        self._execute(task_id, provider, retries, target_count)
        return self.get_task(task_id) or {}


def source_label(provider: str) -> str:
    mapping = {
        "jobsie": "jobs.ie",
        "irishjobs": "irishjobs.ie",
        "linkedin": "linkedin",
        "all": "all",
    }
    return mapping[provider]


def is_rate_limited(provider: str, session: Session) -> bool:
    if provider == "all":
        return False
    last_run = (
        session.query(ScraperRun)
        .filter_by(source=source_label(provider))
        .order_by(ScraperRun.started_at.desc())
        .first()
    )
    if not last_run or not last_run.started_at:
        return False
    threshold = datetime.utcnow() - timedelta(seconds=max(10, config.RATE_LIMIT_PERIOD_SECONDS))
    return last_run.started_at > threshold
