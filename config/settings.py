import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    POSTGRES_HOST = os.getenv('POSTGRES_HOST') or 'localhost'
    POSTGRES_PORT = os.getenv('POSTGRES_PORT') or '5432'
    POSTGRES_DB = os.getenv('POSTGRES_DB') or 'jobfit_ai'
    POSTGRES_USER = os.getenv('POSTGRES_USER') or 'postgres'
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD') or 'password'
    
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST') or 'localhost'
    REDIS_PORT = int(os.getenv('REDIS_PORT') or '6379')
    REDIS_DB = int(os.getenv('REDIS_DB') or '0')
    
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # API Keys
    FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    APIFY_TOKEN = os.getenv('APIFY_TOKEN', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'models/embedding-001')
    
    # Scraper
    MAX_PAGES = int(os.getenv('MAX_PAGES', '10'))
    REQUEST_DELAY = int(os.getenv('REQUEST_DELAY', '3'))
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '10'))
    GENERATION_THRESHOLD = int(os.getenv('GENERATION_THRESHOLD', '80'))
    
    # Base URLs
    JOBS_IE_BASE_URL = os.getenv('JOBS_IE_BASE_URL', 'https://www.jobs.ie')
    JOBS_IE_SEARCH_URL = os.getenv('JOBS_IE_SEARCH_URL', 'https://www.jobs.ie/jobs')
    IRISH_JOBS_BASE_URL = os.getenv('IRISH_JOBS_BASE_URL', 'https://www.irishjobs.ie')
    IRISH_JOBS_SEARCH_URL = os.getenv('IRISH_JOBS_SEARCH_URL', 'https://www.irishjobs.ie/Jobs')
    LINKEDIN_IE_BASE_URL = os.getenv('LINKEDIN_IE_BASE_URL', 'https://ie.linkedin.com/jobs')
    
    # LinkedIn specific
    LINKEDIN_GEO_ID = os.getenv('LINKEDIN_GEO_ID', '104738515')  # Ireland geoId
    LINKEDIN_DAYS = os.getenv('LINKEDIN_DAYS', '7')  # Last 7 days
    
    # Embedding
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    EMBEDDING_DIMENSIONS = int(os.getenv('EMBEDDING_DIMENSIONS', '384'))
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')
    
    # Agent
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-4o')
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2000'))
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

    # Security / Auth
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'clover-dev-secret-change-me')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES_MINUTES', '45'))
    JWT_REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES_DAYS', '14'))
    
    # File Upload
    MAX_CV_SIZE_MB = int(os.getenv('MAX_CV_SIZE_MB', '5'))
    ALLOWED_CV_EXTENSIONS = os.getenv('ALLOWED_CV_EXTENSIONS', 'pdf,docx').split(',')
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', './uploads')
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8000'))
    API_DEBUG = os.getenv('API_DEBUG', 'False').lower() == 'true'
    
    # Session
    SESSION_EXPIRY_HOURS = int(os.getenv('SESSION_EXPIRY_HOURS', '24'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_DIR = os.getenv('LOG_DIR', './logs')
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_PERIOD_SECONDS = int(os.getenv('RATE_LIMIT_PERIOD_SECONDS', '60'))
    
    @classmethod
    def validate(cls, report: bool = True, require_optional: bool = False):
        errors = []
        warnings = []

        required_settings = {
            "POSTGRES_HOST": cls.POSTGRES_HOST,
            "POSTGRES_PORT": cls.POSTGRES_PORT,
            "POSTGRES_DB": cls.POSTGRES_DB,
            "POSTGRES_USER": cls.POSTGRES_USER,
            "POSTGRES_PASSWORD": cls.POSTGRES_PASSWORD,
        }

        optional_settings = {
            "APIFY_TOKEN": cls.APIFY_TOKEN,
            "GEMINI_API_KEY": cls.GEMINI_API_KEY,
            "FIRECRAWL_API_KEY": cls.FIRECRAWL_API_KEY,
            "OPENAI_API_KEY": cls.OPENAI_API_KEY,
        }

        for key, value in required_settings.items():
            if value in (None, ""):
                errors.append(f"{key} is not set")

        for key, value in optional_settings.items():
            if value in (None, ""):
                message = f"{key} is not set"
                if require_optional:
                    errors.append(message)
                else:
                    warnings.append(message)

        if errors:
            if report:
                for error in errors:
                    print(f"Configuration Error: {error}")
            return False

        if report and warnings:
            for warning in warnings:
                print(f"Configuration Warning: {warning}")

        return True

    @classmethod
    def display(cls):
        settings = {
            "DATABASE_URL": cls.DATABASE_URL,
            "REDIS_URL": cls.REDIS_URL,
            "API_HOST": cls.API_HOST,
            "API_PORT": cls.API_PORT,
            "API_DEBUG": cls.API_DEBUG,
            "GENERATION_THRESHOLD": cls.GENERATION_THRESHOLD,
            "CHROMA_DB_PATH": cls.CHROMA_DB_PATH,
            "UPLOAD_DIR": cls.UPLOAD_DIR,
            "MAX_PAGES": cls.MAX_PAGES,
            "REQUEST_DELAY": cls.REQUEST_DELAY,
            "APIFY_TOKEN_CONFIGURED": bool(cls.APIFY_TOKEN),
            "GEMINI_API_KEY_CONFIGURED": bool(cls.GEMINI_API_KEY),
            "FIRECRAWL_API_KEY_CONFIGURED": bool(cls.FIRECRAWL_API_KEY),
            "OPENAI_API_KEY_CONFIGURED": bool(cls.OPENAI_API_KEY),
            "JWT_ALGORITHM": cls.JWT_ALGORITHM,
            "JWT_ACCESS_TOKEN_EXPIRES_MINUTES": cls.JWT_ACCESS_TOKEN_EXPIRES_MINUTES,
            "JWT_REFRESH_TOKEN_EXPIRES_DAYS": cls.JWT_REFRESH_TOKEN_EXPIRES_DAYS,
        }

        for key, value in settings.items():
            print(f"{key}: {value}")

config = Config()
config.validate(report=False)
