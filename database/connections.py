from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import logging

from config.settings import config
from scraper.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.session_factory = None
        
    def init_db(self, create_tables=True):
        try:
            self.engine = create_engine(
                config.DATABASE_URL,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            self.session_factory = scoped_session(sessionmaker(bind=self.engine))
            
            if create_tables:
                Base.metadata.create_all(self.engine)
                self._run_lightweight_migrations()
                logger.info("Database tables created")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def get_session(self):
        if not self.session_factory:
            self.init_db()
        return self.session_factory()
    
    def close_all(self):
        if self.session_factory:
            self.session_factory.remove()
        if self.engine:
            self.engine.dispose()

    def _run_lightweight_migrations(self):
        """
        Lightweight, idempotent schema updates for environments without Alembic.
        """
        if not self.engine:
            return
        statements = [
            "ALTER TABLE match_results ADD COLUMN IF NOT EXISTS personalized_fit_score NUMERIC(5,2)",
            "ALTER TABLE match_results ADD COLUMN IF NOT EXISTS adaptive_boost NUMERIC(5,2)",
            "ALTER TABLE match_results ADD COLUMN IF NOT EXISTS fit_explanation TEXT",
            "ALTER TABLE match_results ADD COLUMN IF NOT EXISTS resume_version INTEGER DEFAULT 1",
            "ALTER TABLE match_results ADD COLUMN IF NOT EXISTS confidence NUMERIC(5,2) DEFAULT 0",
            "ALTER TABLE match_results ADD COLUMN IF NOT EXISTS match_label VARCHAR(40) DEFAULT 'Moderate Match'",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS fit_explanation TEXT",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS keyword_justifications JSON",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS cv_diff JSON",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS keywords_added JSON",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS optimized_resume_path TEXT",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS cover_letter_path TEXT",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS profile_id VARCHAR(36)",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS job_id VARCHAR(36)",
            "ALTER TABLE generated_outputs ADD COLUMN IF NOT EXISTS resume_version INTEGER DEFAULT 1",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS phone VARCHAR(64)",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS parsed_resume_data JSON",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS resume_version INTEGER DEFAULT 1",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
            "ALTER TABLE user_applications ADD COLUMN IF NOT EXISTS resume_version INTEGER DEFAULT 1",
            "ALTER TABLE user_applications ADD COLUMN IF NOT EXISTS deadline_at TIMESTAMP",
            "ALTER TABLE user_applications ADD COLUMN IF NOT EXISTS next_action TEXT",
            "ALTER TABLE user_applications ADD COLUMN IF NOT EXISTS last_agent_summary TEXT",
            """
            CREATE TABLE IF NOT EXISTS resume_documents (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36),
                profile_id VARCHAR(36) NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                original_filename VARCHAR(255) NOT NULL,
                storage_path TEXT NOT NULL,
                mime_type VARCHAR(100),
                file_size_bytes INTEGER,
                parsed_data JSON,
                uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
                is_active BOOLEAN NOT NULL DEFAULT TRUE
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_resume_documents_user_id ON resume_documents (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_resume_documents_profile_id ON resume_documents (profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_generated_outputs_profile_id ON generated_outputs (profile_id)",
            "CREATE INDEX IF NOT EXISTS idx_generated_outputs_job_id ON generated_outputs (job_id)",
            "CREATE INDEX IF NOT EXISTS idx_generated_outputs_resume_version ON generated_outputs (resume_version)",
            "CREATE INDEX IF NOT EXISTS idx_match_results_resume_version ON match_results (resume_version)",
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles (user_id)",
        ]
        try:
            with self.engine.begin() as conn:
                for stmt in statements:
                    conn.execute(text(stmt))
        except Exception as exc:
            logger.warning(f"Schema migration warning: {exc}")

db_manager = DatabaseManager()
