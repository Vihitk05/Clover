import json
import logging
from typing import Dict, List

from agents.gemini_client import GeminiClient
from config.settings import config

logger = logging.getLogger(__name__)


class JobEmbedder:
    """Embeds scraped jobs and stores vectors in ChromaDB."""

    def __init__(self, persist_directory: str | None = None):
        self.gemini = GeminiClient()
        self.persist_directory = persist_directory or config.CHROMA_DB_PATH
        self.collection = None
        self._init_chroma()

    def _init_chroma(self) -> None:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=self.persist_directory)
            try:
                self.collection = client.get_collection("job_embeddings")
            except Exception:
                self.collection = client.create_collection(
                    name="job_embeddings",
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as exc:
            logger.warning(f"Chroma init failed for JobEmbedder: {exc}")
            self.collection = None

    @staticmethod
    def _job_text(job: Dict) -> str:
        parts = [
            f"Title: {job.get('title', '')}",
            f"Company: {job.get('company', '')}",
            f"Location: {job.get('location', '')}",
            f"Seniority: {job.get('seniority', '')}",
            f"Skills: {', '.join(job.get('skills_extracted', []) or [])}",
            f"Description: {job.get('description_raw', '')}",
        ]
        return " | ".join(parts)

    def embed_jobs(self, jobs: List[Dict]) -> bool:
        if not jobs:
            return True
        if self.collection is None:
            logger.warning("Job embedding skipped; Chroma collection unavailable.")
            return False

        ids: List[str] = []
        embeddings: List[List[float]] = []
        metadatas: List[Dict] = []
        documents: List[str] = []

        for job in jobs:
            job_id = str(job.get("id") or "")
            if not job_id:
                continue
            text = self._job_text(job)
            vector = self.gemini.embed_text(text, dimensions=config.EMBEDDING_DIMENSIONS)
            ids.append(job_id)
            embeddings.append(vector)
            documents.append(job.get("description_raw", ""))
            metadatas.append(
                {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "seniority": job.get("seniority", ""),
                    "skills_extracted": json.dumps(job.get("skills_extracted", []) or []),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "source": job.get("source", ""),
                }
            )

        if not ids:
            return True

        try:
            # Upsert for idempotence across periodic scrapes.
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            logger.info(f"Embedded and upserted {len(ids)} jobs into ChromaDB.")
            return True
        except Exception as exc:
            logger.error(f"Failed to write job embeddings: {exc}")
            return False
