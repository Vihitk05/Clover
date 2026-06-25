import html
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup


def _first_present(data: Dict[str, Any], aliases: Iterable[str]) -> Any:
    lowered = {str(key).lower(): value for key, value in data.items()}
    for alias in aliases:
        if alias in data and data[alias] not in (None, ""):
            return data[alias]
        value = lowered.get(alias.lower())
        if value not in (None, ""):
            return value
    return None


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@dataclass
class IngestedJobListing:
    title: str = ""
    company: str = ""
    location: str = ""
    description_raw: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "EUR"
    salary_period: Optional[str] = None
    seniority: str = "Mid"
    sector: str = "Technology"
    skills_extracted: List[str] = field(default_factory=list)
    source: str = "unknown"
    url: str = ""
    posted_at: Optional[datetime] = None
    employment_type: Optional[str] = None
    work_type: Optional[str] = None
    language: str = "unknown"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JobListingIngestionPipeline:
    """Normalize multilingual job listings from HTML, JSON, and scraper payloads."""

    FIELD_ALIASES = {
        "title": [
            "title",
            "jobTitle",
            "job_title",
            "position",
            "role",
            "headline",
            "name",
            "puesto",
            "titulo",
            "titre",
            "poste",
            "stellenbezeichnung",
            "functie",
            "ruolo",
        ],
        "company": [
            "company",
            "companyName",
            "company_name",
            "employer",
            "hiringOrganization",
            "organization",
            "empresa",
            "société",
            "societe",
            "unternehmen",
            "azienda",
        ],
        "location": [
            "location",
            "jobLocation",
            "job_location",
            "address",
            "city",
            "localidad",
            "ubicacion",
            "lieu",
            "standort",
            "plaats",
            "sede",
        ],
        "description": [
            "description_raw",
            "description",
            "descriptionText",
            "descriptionHtml",
            "summary",
            "body",
            "responsibilities",
            "requirements",
            "descripcion",
            "descripción",
            "description_du_poste",
            "beschreibung",
            "omschrijving",
            "descrizione",
        ],
        "salary": [
            "salary_raw",
            "salary",
            "salaryInfo",
            "baseSalary",
            "compensation",
            "pay",
            "remuneration",
            "salario",
            "salaire",
            "gehalt",
            "salaris",
            "stipendio",
        ],
        "posted_at": [
            "posted_at",
            "postedAt",
            "datePosted",
            "publishedAt",
            "createdAt",
            "fecha",
            "date",
            "datum",
        ],
        "employment_type": [
            "employment_type",
            "employmentType",
            "contractType",
            "jobType",
            "tipo_contrato",
            "type_de_contrat",
            "vertragsart",
        ],
        "work_type": [
            "work_type",
            "workplaceType",
            "workplaceTypes",
            "remote",
            "remoteType",
            "modalidad",
            "arbeitsort",
        ],
        "url": ["url", "link", "jobUrl", "canonicalUrl", "applyUrl"],
        "source": ["source", "source_name", "platform"],
    }

    SKILL_ALIASES = {
        "Python": ["python"],
        "Java": ["java"],
        "JavaScript": ["javascript", "java script", "js"],
        "TypeScript": ["typescript", "type script", "ts"],
        "React": ["react", "react.js", "reactjs"],
        "Angular": ["angular", "angular.js"],
        "Vue.js": ["vue", "vue.js", "vuejs"],
        "Node.js": ["node", "node.js", "nodejs"],
        "Django": ["django"],
        "Flask": ["flask"],
        "FastAPI": ["fastapi", "fast api"],
        "AWS": ["aws", "amazon web services"],
        "Azure": ["azure", "microsoft azure"],
        "GCP": ["gcp", "google cloud", "google cloud platform"],
        "Docker": ["docker"],
        "Kubernetes": ["kubernetes", "k8s"],
        "PostgreSQL": ["postgresql", "postgres"],
        "MySQL": ["mysql"],
        "MongoDB": ["mongodb", "mongo db"],
        "Redis": ["redis"],
        "SQL": ["sql", "sql server", "t-sql", "tsql"],
        "Machine Learning": ["machine learning", "aprendizaje automático", "apprentissage automatique", "maschinelles lernen"],
        "Data Science": ["data science", "ciencia de datos", "science des données", "datenwissenschaft"],
        "TensorFlow": ["tensorflow"],
        "PyTorch": ["pytorch", "torch"],
        "REST API": ["rest api", "restful", "api rest"],
        "GraphQL": ["graphql"],
        "Git": ["git", "github", "gitlab"],
        "Agile": ["agile", "ágil", "scrum agile"],
        "Scrum": ["scrum"],
        "Pandas": ["pandas"],
        "NumPy": ["numpy"],
        "Scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
        "Tableau": ["tableau"],
        "Power BI": ["power bi", "powerbi"],
        "NLP": ["nlp", "natural language processing", "procesamiento del lenguaje natural", "traitement automatique du langage"],
        "Deep Learning": ["deep learning", "aprendizaje profundo", "apprentissage profond", "tiefes lernen"],
        "Transformers": ["transformers", "hugging face", "huggingface"],
        "Spark": ["spark", "apache spark"],
        "Airflow": ["airflow", "apache airflow"],
        "ETL": ["etl", "elt"],
        "CI/CD": ["ci/cd", "cicd", "continuous integration", "continuous delivery"],
        "Linux": ["linux"],
        "Terraform": ["terraform"],
        "Ansible": ["ansible"],
        "Excel": ["excel", "microsoft excel"],
        "Figma": ["figma"],
        "Salesforce": ["salesforce"],
        "SAP": ["sap"],
        "Kotlin": ["kotlin"],
        "Swift": ["swift"],
        "PHP": ["php"],
        "Ruby": ["ruby", "ruby on rails", "rails"],
        "Go": ["golang", "go"],
        "Rust": ["rust"],
        "C#": ["c#", "c sharp"],
        "C++": ["c++", "cplusplus"],
        ".NET": [".net", "dotnet", "asp.net"],
    }

    LANGUAGE_MARKERS = {
        "en": ["responsibilities", "requirements", "experience", "salary", "remote", "skills"],
        "es": ["responsabilidades", "requisitos", "experiencia", "salario", "remoto", "habilidades", "ingeniero", "datos", "espana", "españa", "hibrido", "híbrido"],
        "fr": ["responsabilites", "responsabilités", "exigences", "experience", "expérience", "salaire", "teletravail", "télétravail", "competences", "compétences"],
        "de": ["aufgaben", "anforderungen", "erfahrung", "gehalt", "kenntnisse", "homeoffice"],
        "pt": ["responsabilidades", "requisitos", "experiencia", "experiência", "salario", "salário", "remoto", "engenheiro", "dados"],
        "nl": ["verantwoordelijkheden", "vereisten", "ervaring", "salaris", "vaardigheden"],
        "it": ["responsabilita", "responsabilità", "requisiti", "esperienza", "stipendio", "competenze"],
    }

    SENIORITY_PATTERNS = [
        ("Lead", ["lead", "manager", "director", "head", "leiter", "responsable", "jefe", "chef", "principal"]),
        ("Senior", ["senior", "sr", "staff", "sénior", "experimentado", "confirmé", "experimente", "erfahren"]),
        ("Junior", ["junior", "jr", "entry", "graduate", "trainee", "débutant", "debutant", "júnior", "praticante"]),
        ("Intern", ["intern", "internship", "stagiaire", "werkstudent", "prácticas", "practicas", "stage"]),
    ]

    SECTOR_PATTERNS = {
        "Fintech": ["fintech", "banking", "finance", "payments", "banco", "finanzas", "banque", "paiements", "bankwesen"],
        "Healthcare": ["healthcare", "medical", "clinical", "health", "salud", "santé", "sante", "medizin", "zorg"],
        "SaaS": ["saas", "software as a service", "cloud software", "logiciel cloud", "software-as-a-service"],
        "E-commerce": ["e-commerce", "ecommerce", "retail", "commerce électronique", "comercio electrónico", "handel"],
        "Consulting": ["consulting", "consultancy", "conseil", "beratung", "consultoría", "consultoria"],
        "Education": ["education", "edtech", "university", "school", "éducation", "educación", "bildung"],
    }

    CURRENCY_SYMBOLS = {
        "€": "EUR",
        "$": "USD",
        "£": "GBP",
        "¥": "JPY",
    }

    CURRENCY_CODES = {"EUR", "USD", "GBP", "CHF", "CAD", "AUD", "JPY", "SEK", "NOK", "DKK", "PLN"}

    def ingest(self, raw: Any, default_source: str = "unknown") -> Dict[str, Any]:
        data = self._coerce_mapping(raw)
        title = self.clean_text(self._stringify_field(_first_present(data, self.FIELD_ALIASES["title"])))
        company = self.clean_text(self._extract_company(_first_present(data, self.FIELD_ALIASES["company"])))
        location = self.normalize_location(self._stringify_field(_first_present(data, self.FIELD_ALIASES["location"])))
        description = self.clean_text(self._description_from(data, raw))
        source = self.clean_text(self._stringify_field(_first_present(data, self.FIELD_ALIASES["source"]))) or default_source
        url = self.clean_text(self._stringify_field(_first_present(data, self.FIELD_ALIASES["url"])))

        salary = self.parse_salary(_first_present(data, self.FIELD_ALIASES["salary"]))
        if salary.get("min") is None and salary.get("max") is None:
            salary = self.parse_salary(description)
        salary_min = self._coerce_int(data.get("salary_min")) or salary.get("min")
        salary_max = self._coerce_int(data.get("salary_max")) or salary.get("max")

        skills = self.extract_skills(" ".join([title, description, self._stringify_field(data.get("skills_extracted"))]))
        provided_skills = self._canonicalize_provided_skills(data.get("skills_extracted"))
        skills = list(dict.fromkeys([*provided_skills, *skills]))

        text_blob = " ".join([title, company, location, description])
        listing = IngestedJobListing(
            title=title,
            company=company or "Unknown company",
            location=location,
            description_raw=description,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary.get("currency", "EUR"),
            salary_period=salary.get("period"),
            seniority=self.extract_seniority(title, description),
            sector=self.extract_sector(title, description),
            skills_extracted=skills,
            source=source,
            url=url,
            posted_at=self.parse_posted_at(_first_present(data, self.FIELD_ALIASES["posted_at"])),
            employment_type=self.extract_employment_type(_first_present(data, self.FIELD_ALIASES["employment_type"]) or text_blob),
            work_type=self.extract_work_type(_first_present(data, self.FIELD_ALIASES["work_type"]) or text_blob),
            language=self.detect_language(text_blob),
        )

        if not listing.title:
            listing.warnings.append("missing_title")
        if not description:
            listing.warnings.append("missing_description")
        if salary_min and salary_max and salary_min > salary_max:
            listing.salary_min, listing.salary_max = salary_max, salary_min

        return listing.to_dict()

    def clean_text(self, text: Any) -> str:
        if text in (None, ""):
            return ""
        if isinstance(text, (dict, list)):
            text = self._stringify_field(text)
        text = html.unescape(str(text))
        if "<" in text and ">" in text:
            text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
        text = re.sub(r"[\u00a0\t\r\n]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def normalize_location(self, location: Any) -> str:
        text = self.clean_text(location)
        if not text:
            return ""
        lowered = _strip_accents(text.lower())
        if any(token in lowered for token in ["remote", "remoto", "teletravail", "télétravail", "homeoffice", "work from home"]):
            return "Remote"
        if any(token in lowered for token in ["hybrid", "hibrido", "hybride", "hybridarbeit"]):
            return "Hybrid"

        known = {
            "dublin": "Dublin",
            "cork": "Cork",
            "galway": "Galway",
            "limerick": "Limerick",
            "waterford": "Waterford",
            "london": "London",
            "berlin": "Berlin",
            "paris": "Paris",
            "madrid": "Madrid",
            "barcelona": "Barcelona",
            "lisbon": "Lisbon",
            "amsterdam": "Amsterdam",
        }
        for key, normalized in known.items():
            if re.search(rf"\b{re.escape(key)}\b", lowered):
                return normalized
        return ", ".join(part.strip().title() for part in text.split(",")[:2] if part.strip())

    def parse_salary(self, salary: Any) -> Dict[str, Any]:
        result: Dict[str, Any] = {"min": None, "max": None, "currency": "EUR", "period": None}
        if salary in (None, ""):
            return result
        if isinstance(salary, list):
            text = " - ".join(self._stringify_field(item) for item in salary if item not in (None, ""))
        elif isinstance(salary, dict):
            result.update(self._parse_structured_salary(salary))
            text = self._stringify_field(salary)
        else:
            text = str(salary)

        text = self.clean_text(text)
        if not text:
            return result
        result["currency"] = self._detect_currency(text)
        result["period"] = self._detect_salary_period(text)
        amounts = self._extract_salary_amounts(text)
        if amounts:
            result["min"] = min(amounts[:2]) if len(amounts) > 1 else amounts[0]
            result["max"] = max(amounts[:2]) if len(amounts) > 1 else amounts[0]
        return result

    def extract_skills(self, text: Any) -> List[str]:
        haystack = f" {_strip_accents(self.clean_text(text).lower())} "
        found: List[str] = []
        for canonical, aliases in self.SKILL_ALIASES.items():
            for alias in aliases:
                normalized_alias = _strip_accents(alias.lower())
                if re.search(rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])", haystack):
                    found.append(canonical)
                    break
        return list(dict.fromkeys(found))

    def extract_seniority(self, title: Any, description: Any = "") -> str:
        text = _strip_accents(self.clean_text(f"{title} {description}").lower())
        for level, patterns in self.SENIORITY_PATTERNS:
            if any(re.search(rf"\b{re.escape(pattern)}\b", text) for pattern in patterns):
                return level
        return "Mid"

    def extract_sector(self, title: Any, description: Any = "") -> str:
        text = _strip_accents(self.clean_text(f"{title} {description}").lower())
        for sector, patterns in self.SECTOR_PATTERNS.items():
            if any(pattern in text for pattern in [_strip_accents(item.lower()) for item in patterns]):
                return sector
        return "Technology"

    def extract_work_type(self, value: Any) -> Optional[str]:
        text = _strip_accents(self.clean_text(value).lower())
        if any(token in text for token in ["remote", "remoto", "teletravail", "homeoffice", "work from home"]):
            return "Remote"
        if any(token in text for token in ["hybrid", "hibrido", "hybride", "hybridarbeit"]):
            return "Hybrid"
        if any(token in text for token in ["on-site", "onsite", "office", "presencial", "sur site", "vor ort"]):
            return "On-site"
        return None

    def extract_employment_type(self, value: Any) -> Optional[str]:
        text = _strip_accents(self.clean_text(value).lower())
        if any(token in text for token in ["full-time", "full time", "permanent", "tiempo completo", "temps plein", "vollzeit"]):
            return "Full-time"
        if any(token in text for token in ["part-time", "part time", "tiempo parcial", "temps partiel", "teilzeit"]):
            return "Part-time"
        if any(token in text for token in ["contract", "contractor", "freelance", "contrato", "cdd", "befristet"]):
            return "Contract"
        if any(token in text for token in ["intern", "internship", "practicas", "prácticas", "stage", "werkstudent"]):
            return "Internship"
        return None

    def detect_language(self, text: Any) -> str:
        normalized = _strip_accents(self.clean_text(text).lower())
        if not normalized:
            return "unknown"
        scores = {
            code: sum(1 for marker in markers if _strip_accents(marker.lower()) in normalized)
            for code, markers in self.LANGUAGE_MARKERS.items()
        }
        language, score = max(scores.items(), key=lambda item: item[1])
        return language if score > 0 else "unknown"

    def parse_posted_at(self, value: Any) -> Optional[datetime]:
        if value in (None, "") or isinstance(value, (dict, list)):
            return None
        text = self.clean_text(value)
        if not text:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                parsed = datetime.strptime(text[:25], fmt)
                return parsed.replace(tzinfo=None)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _coerce_mapping(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            data = dict(raw)
        elif isinstance(raw, str):
            data = self._mapping_from_string(raw)
        else:
            data = {}
        return self._flatten_common_nested_fields(data)

    def _mapping_from_string(self, raw: str) -> Dict[str, Any]:
        soup = BeautifulSoup(raw, "html.parser")
        data: Dict[str, Any] = {}
        for script in soup.find_all("script", attrs={"type": lambda value: value and "ld+json" in value}):
            try:
                parsed = json.loads(script.string or script.get_text())
            except Exception:
                continue
            nodes = parsed if isinstance(parsed, list) else [parsed]
            for node in nodes:
                if isinstance(node, dict) and str(node.get("@type", "")).lower() == "jobposting":
                    data.update(node)
                    break
        text = soup.get_text("\n", strip=True) if "<" in raw and ">" in raw else raw
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = _strip_accents(key.strip().lower().replace(" ", "_"))
            if normalized_key and value.strip():
                data.setdefault(normalized_key, value.strip())
        data.setdefault("description_raw", text)
        return data

    def _flatten_common_nested_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        flattened = dict(data)
        company = flattened.get("hiringOrganization") or flattened.get("company")
        if isinstance(company, dict):
            flattened.setdefault("company", company.get("name"))
        location = flattened.get("jobLocation") or flattened.get("location")
        if isinstance(location, list):
            location = location[0] if location else {}
        if isinstance(location, dict):
            address = location.get("address", location)
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("addressCountry"),
                ]
                flattened.setdefault("location", ", ".join(str(part) for part in parts if part))
        return flattened

    def _description_from(self, data: Dict[str, Any], raw: Any) -> str:
        description = _first_present(data, self.FIELD_ALIASES["description"])
        if description:
            return self.clean_text(description)
        if isinstance(raw, str):
            return self.clean_text(raw)
        return ""

    def _extract_company(self, value: Any) -> str:
        if isinstance(value, dict):
            return self._stringify_field(value.get("name") or value.get("companyName"))
        return self._stringify_field(value)

    def _stringify_field(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, list):
            return " ".join(self._stringify_field(item) for item in value if item not in (None, ""))
        if isinstance(value, dict):
            useful = [value.get(key) for key in ("name", "title", "text", "value", "minValue", "maxValue") if value.get(key)]
            if useful:
                return " ".join(str(item) for item in useful)
            return " ".join(str(item) for item in value.values() if item not in (None, "", [], {}))
        return str(value)

    def _parse_structured_salary(self, salary: Dict[str, Any]) -> Dict[str, Any]:
        value = salary.get("value") if isinstance(salary.get("value"), dict) else salary
        result = {
            "min": self._coerce_int(value.get("minValue") or value.get("min")),
            "max": self._coerce_int(value.get("maxValue") or value.get("max")),
            "currency": salary.get("currency") or salary.get("currencyCode") or "EUR",
            "period": value.get("unitText") or value.get("period"),
        }
        if result["min"] and result["max"] and result["min"] > result["max"]:
            result["min"], result["max"] = result["max"], result["min"]
        return result

    def _canonicalize_provided_skills(self, skills: Any) -> List[str]:
        if not skills:
            return []
        values = skills if isinstance(skills, list) else re.split(r"[,;/|]", str(skills))
        canonical_lookup = {
            _strip_accents(alias.lower()): canonical
            for canonical, aliases in self.SKILL_ALIASES.items()
            for alias in aliases + [canonical]
        }
        result = []
        for value in values:
            cleaned = self.clean_text(value)
            result.append(canonical_lookup.get(_strip_accents(cleaned.lower()), cleaned))
        return [skill for skill in dict.fromkeys(result) if skill]

    def _detect_currency(self, text: str) -> str:
        for symbol, code in self.CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code
        upper = text.upper()
        for code in self.CURRENCY_CODES:
            if re.search(rf"\b{code}\b", upper):
                return code
        return "EUR"

    def _detect_salary_period(self, text: str) -> Optional[str]:
        normalized = _strip_accents(text.lower())
        if any(token in normalized for token in ["hour", "hora", "heure", "stunde"]):
            return "hour"
        if any(token in normalized for token in ["day", "jour", "tag", "día", "dia"]):
            return "day"
        if any(token in normalized for token in ["month", "mes", "mois", "monat"]):
            return "month"
        if any(token in normalized for token in ["year", "annual", "annum", "año", "ano", "année", "par an", "jahr", "pa", "p.a."]):
            return "year"
        return None

    def _extract_salary_amounts(self, text: str) -> List[int]:
        amounts: List[int] = []
        amount_pattern = re.compile(r"(?<!\w)(?:[€$£]\s*)?(\d{1,3}(?:[.,\s]\d{3})+|\d+(?:[.,]\d+)?)(?:\s*(k|K))?")
        for match in amount_pattern.finditer(text):
            raw_number, suffix = match.groups()
            value = self._parse_number(raw_number)
            if value is None:
                continue
            if suffix or value < 1000 and re.search(rf"{re.escape(match.group(0))}\s*(?:k|K)\b", text):
                value *= 1000
            if value >= 10:
                amounts.append(int(round(value)))
        return amounts

    def _parse_number(self, raw: str) -> Optional[float]:
        if not raw:
            return None
        value = raw.strip()
        value = re.sub(r"\s+", "", value)
        if "," in value and "." in value:
            decimal = "," if value.rfind(",") > value.rfind(".") else "."
            thousands = "." if decimal == "," else ","
            value = value.replace(thousands, "").replace(decimal, ".")
        elif "," in value:
            parts = value.split(",")
            value = "".join(parts) if len(parts[-1]) == 3 else value.replace(",", ".")
        elif "." in value:
            parts = value.split(".")
            value = "".join(parts) if len(parts[-1]) == 3 else value
        try:
            return float(value)
        except ValueError:
            return None

    def _coerce_int(self, value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        parsed = self._parse_number(str(value))
        return int(parsed) if parsed is not None else None
