from scraper.etl.cleaner import DataCleaner
from scraper.etl.job_ingestion import JobListingIngestionPipeline


def test_ingests_spanish_api_payload_with_structured_metadata():
    pipeline = JobListingIngestionPipeline()

    result = pipeline.ingest(
        {
            "puesto": "Ingeniero Senior de Datos",
            "empresa": "Banco Verde",
            "ubicacion": "Madrid, España - híbrido",
            "descripcion": "Responsabilidades: construir pipelines ETL con Python, SQL, Spark y Airflow. Salario €45k-€60k.",
            "tipo_contrato": "tiempo completo",
            "source": "partner_api",
        }
    )

    assert result["title"] == "Ingeniero Senior de Datos"
    assert result["company"] == "Banco Verde"
    assert result["location"] == "Hybrid"
    assert result["language"] == "es"
    assert result["seniority"] == "Senior"
    assert result["salary_min"] == 45000
    assert result["salary_max"] == 60000
    assert result["employment_type"] == "Full-time"
    assert {"Python", "SQL", "Spark", "Airflow", "ETL"}.issubset(set(result["skills_extracted"]))


def test_ingests_german_listing_with_european_salary_format():
    pipeline = JobListingIngestionPipeline()

    result = pipeline.ingest(
        {
            "stellenbezeichnung": "Junior Backend Entwickler",
            "unternehmen": "Mittelstand Cloud GmbH",
            "standort": "Berlin",
            "beschreibung": "Anforderungen: Erfahrung mit Java, Docker, Kubernetes und PostgreSQL. Gehalt 40.000 - 55.000 EUR pro Jahr.",
        }
    )

    assert result["language"] == "de"
    assert result["seniority"] == "Junior"
    assert result["location"] == "Berlin"
    assert result["salary_min"] == 40000
    assert result["salary_max"] == 55000
    assert {"Java", "Docker", "Kubernetes", "PostgreSQL"}.issubset(set(result["skills_extracted"]))


def test_ingests_json_ld_html_job_posting():
    pipeline = JobListingIngestionPipeline()
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@type": "JobPosting",
          "title": "Machine Learning Engineer",
          "hiringOrganization": {"name": "Clover Labs"},
          "jobLocation": {"address": {"addressLocality": "Dublin", "addressCountry": "IE"}},
          "description": "<p>Requirements: Python, PyTorch, NLP, Transformers. Remote friendly.</p>",
          "baseSalary": {"currency": "EUR", "value": {"minValue": 70000, "maxValue": 90000, "unitText": "YEAR"}}
        }
        </script>
      </head>
    </html>
    """

    result = pipeline.ingest(html, default_source="json_ld")

    assert result["title"] == "Machine Learning Engineer"
    assert result["company"] == "Clover Labs"
    assert result["location"] == "Dublin"
    assert result["work_type"] == "Remote"
    assert result["salary_min"] == 70000
    assert result["salary_max"] == 90000
    assert result["salary_period"] == "year"
    assert {"Python", "PyTorch", "NLP", "Transformers"}.issubset(set(result["skills_extracted"]))


def test_data_cleaner_keeps_existing_salary_and_skill_contracts():
    cleaner = DataCleaner()

    salary = cleaner.parse_salary("£500 - £650 per day")
    skills = cleaner.extract_skills("Experienced with FastAPI, PostgreSQL, CI/CD and Google Cloud Platform.")

    assert salary["min"] == 500
    assert salary["max"] == 650
    assert salary["currency"] == "GBP"
    assert salary["period"] == "day"
    assert {"FastAPI", "PostgreSQL", "CI/CD", "GCP"}.issubset(set(skills))


def test_save_job_persists_normalized_ingestion_metadata():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from scraper.models import Base
    from scraper.run_scraper import save_job

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    try:
        saved = save_job(
            {
                "titre": "Développeur Senior Python",
                "société": "Clover France",
                "lieu": "Paris - télétravail",
                "description_du_poste": "Compétences: Python, FastAPI, PostgreSQL et Docker. Salaire 65 000 - 80 000 EUR par an.",
                "source": "fixture",
                "url": "https://example.com/jobs/1",
            },
            session,
        )

        assert saved is not None
        assert saved.title == "Développeur Senior Python"
        assert saved.company == "Clover France"
        assert saved.location == "Remote"
        assert saved.seniority == "Senior"
        assert saved.salary_min == 65000
        assert saved.salary_max == 80000
        assert {"Python", "FastAPI", "PostgreSQL", "Docker"}.issubset(set(saved.skills_extracted))
    finally:
        session.close()
