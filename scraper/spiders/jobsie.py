import requests
from bs4 import BeautifulSoup
import time
import logging
from typing import List, Dict, Optional
from datetime import UTC, datetime
import random
import json
import re

from config.settings import config

logger = logging.getLogger(__name__)

class JobsIEDirectSpider:
    """Direct scraper for Jobs.ie using requests and BeautifulSoup"""
    
    def __init__(self):
        self.source_name = 'jobs.ie'
        self.base_url = config.JOBS_IE_BASE_URL
        self.search_url = config.JOBS_IE_SEARCH_URL
        self.session = requests.Session()
        self.start_time = None
        self.stats = {
            'pages_scraped': 0,
            'jobs_found': 0,
            'errors': 0
        }
        
        # Rotate user agents to avoid detection
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ]
    
    def get_headers(self):
        """Get random headers for request"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
    
    def scrape_page(self, page_number: int) -> Optional[str]:
        """Scrape a single page using requests"""
        try:
            url = f"{self.search_url}?page={page_number}"
            logger.info(f"Scraping page {page_number}: {url}")
            
            response = self.session.get(
                url,
                headers=self.get_headers(),
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully scraped page {page_number}")
                return response.text
            elif response.status_code == 403:
                logger.warning(f"Access forbidden for page {page_number}. Waiting longer...")
                time.sleep(10)
                return None
            else:
                logger.warning(f"Failed to scrape page {page_number}. Status: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for page {page_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping page {page_number}: {e}")
            return None
    
    def scrape_all_pages(self, max_pages: int = None) -> List[Dict]:
        """Scrape multiple pages using pagination"""
        if max_pages is None:
            max_pages = config.MAX_PAGES
        
        all_jobs = []
        self.start_time = datetime.utcnow()
        logger.info(f"Starting {self.source_name} direct scraper")
        logger.info(f"URL: {self.search_url}")
        logger.info(f"Max pages: {max_pages}")
        
        for page in range(1, max_pages + 1):
            try:
                # Add random delay to avoid detection
                delay = random.uniform(config.REQUEST_DELAY, config.REQUEST_DELAY * 1.5)
                if page > 1:
                    logger.debug(f"Waiting {delay:.1f} seconds...")
                    time.sleep(delay)
                
                html = self.scrape_page(page)
                
                if html:
                    jobs = self.parse_job_cards_from_html(html, page)
                    
                    if jobs:
                        all_jobs.extend(jobs)
                        self.stats['jobs_found'] += len(jobs)
                        self.stats['pages_scraped'] += 1
                        logger.info(f"Page {page}: Found {len(jobs)} jobs (Total: {len(all_jobs)})")
                    else:
                        logger.warning(f"Page {page}: No jobs found")
                        # If we find 2 consecutive empty pages, stop
                        if page > 2 and len(jobs) == 0:
                            logger.info(f"No jobs on page {page}, assuming end of listings")
                            break
                else:
                    logger.warning(f"Failed to get HTML for page {page}")
                    self.stats['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing page {page}: {e}")
                self.stats['errors'] += 1
                continue
        
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        logger.info(f"Scraping completed. Duration: {duration:.2f}s")
        logger.info(f"Stats: {self.stats}")
        
        return all_jobs
    
    def parse_job_cards_from_html(self, html: str, page_number: int) -> List[Dict]:
        """Parse job cards from listing page HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            cards = self._find_card_candidates(soup)
            if cards:
                logger.debug(f"Processing {len(cards)} cards from page {page_number}")
                jobs = self._extract_jobs_from_cards(cards, page_number=page_number)
                if jobs:
                    return jobs

            # Fallback 1: SEO payloads are often present even when card DOM shifts.
            json_ld_jobs = self._extract_jobs_from_json_ld(soup)
            if json_ld_jobs:
                logger.info(f"Page {page_number}: extracted {len(json_ld_jobs)} jobs via JSON-LD fallback")
                return self._finalize_jobs(json_ld_jobs)

            # Fallback 2: parse Next.js data blob when available.
            embedded_jobs = self._extract_jobs_from_embedded_state(soup)
            if embedded_jobs:
                logger.info(f"Page {page_number}: extracted {len(embedded_jobs)} jobs via embedded state fallback")
                return self._finalize_jobs(embedded_jobs)

            # Fallback 3: link-only extraction to avoid total data loss.
            link_jobs = self._extract_jobs_from_links(soup)
            if link_jobs:
                logger.info(f"Page {page_number}: extracted {len(link_jobs)} jobs via link fallback")
                return self._finalize_jobs(link_jobs)

            return []
        except Exception as e:
            logger.error(f"Error parsing HTML for page {page_number}: {e}")
            return []

    def _finalize_jobs(self, jobs: List[Dict]) -> List[Dict]:
        deduped: List[Dict] = []
        seen: set[str] = set()
        for job in jobs:
            title = str(job.get("title", "")).strip()
            if not title:
                continue
            company = str(job.get("company", "")).strip() or "Unknown company"
            location = str(job.get("location", "")).strip()
            dedupe_key = f"{title.lower()}|{company.lower()}|{location.lower()}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized = {
                **job,
                "company": company,
                "source": self.source_name,
                "scraped_at": datetime.now(UTC).isoformat(),
            }
            deduped.append(normalized)
        return deduped

    def _find_card_candidates(self, soup: BeautifulSoup):
        selectors = [
            'article[data-genesis-element="CARD"]',
            'article.job-card',
            'div[data-at="job-card"]',
            'li.job-listing',
            'div.job-item',
            'div[class*="job-card"]',
            'article[class*="job"]',
            '[data-at*="job"]',
            '[data-testid*="job"]',
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                logger.debug(f"Found {len(cards)} cards using selector: {selector}")
                return cards
        return []

    def _extract_jobs_from_cards(self, cards, page_number: int) -> List[Dict]:
        job_cards: List[Dict] = []
        for card in cards:
            try:
                job_data = self.extract_job_data_from_card(card, page_number)
                if job_data and job_data.get("title"):
                    job_cards.append(job_data)
            except Exception as e:
                logger.debug(f"Error extracting job from card: {e}")
                continue
        return self._finalize_jobs(job_cards)

    def _walk_json_nodes(self, node):
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from self._walk_json_nodes(value)
        elif isinstance(node, list):
            for item in node:
                yield from self._walk_json_nodes(item)

    def _extract_jobs_from_json_ld(self, soup: BeautifulSoup) -> List[Dict]:
        jobs: List[Dict] = []
        scripts = soup.find_all("script", attrs={"type": lambda v: v and "ld+json" in v})
        for script in scripts:
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            for node in self._walk_json_nodes(data):
                if not isinstance(node, dict):
                    continue
                if str(node.get("@type", "")).lower() != "jobposting":
                    continue
                job = {
                    "title": str(node.get("title", "")).strip(),
                    "url": self._normalize_url(str(node.get("url", "")).strip()),
                    "description_raw": BeautifulSoup(str(node.get("description", "")), "html.parser").get_text(" ", strip=True),
                }

                hiring_org = node.get("hiringOrganization")
                if isinstance(hiring_org, dict):
                    job["company"] = str(hiring_org.get("name", "")).strip()
                elif isinstance(hiring_org, str):
                    job["company"] = hiring_org.strip()

                job_location = node.get("jobLocation")
                if isinstance(job_location, list):
                    job_location = job_location[0] if job_location else {}
                if isinstance(job_location, dict):
                    address = job_location.get("address")
                    if isinstance(address, dict):
                        locality = address.get("addressLocality")
                        region = address.get("addressRegion")
                        country = address.get("addressCountry")
                        parts = [str(x).strip() for x in [locality, region, country] if x]
                        if parts:
                            job["location"] = ", ".join(parts[:2])

                posted = node.get("datePosted") or node.get("validThrough")
                if posted:
                    job["posted_at"] = posted

                base_salary = node.get("baseSalary")
                if isinstance(base_salary, dict):
                    value = base_salary.get("value")
                    if isinstance(value, dict):
                        salary_min = value.get("minValue")
                        salary_max = value.get("maxValue")
                        if salary_min and salary_max:
                            job["salary_raw"] = f"{salary_min} - {salary_max}"

                jobs.append(job)
        return jobs

    def _extract_jobs_from_embedded_state(self, soup: BeautifulSoup) -> List[Dict]:
        jobs: List[Dict] = []
        next_data_node = soup.find("script", id="__NEXT_DATA__")
        if not next_data_node:
            return jobs

        raw = next_data_node.string or next_data_node.get_text()
        if not raw:
            return jobs
        try:
            data = json.loads(raw)
        except Exception:
            return jobs

        for node in self._walk_json_nodes(data):
            if not isinstance(node, dict):
                continue
            title = str(node.get("title", "")).strip()
            if len(title) < 3:
                continue

            # Most job payloads include either company + url or location + id.
            possible_company = (
                node.get("company")
                or node.get("companyName")
                or node.get("employer")
                or node.get("hiringOrganization")
            )
            company = ""
            if isinstance(possible_company, dict):
                company = str(possible_company.get("name", "")).strip()
            elif isinstance(possible_company, str):
                company = possible_company.strip()

            url = str(
                node.get("url")
                or node.get("jobUrl")
                or node.get("canonicalUrl")
                or node.get("applyUrl")
                or ""
            ).strip()

            location = str(node.get("location") or node.get("jobLocation") or "").strip()
            if isinstance(node.get("jobLocation"), dict):
                address = node.get("jobLocation", {}).get("address", {})
                locality = address.get("addressLocality")
                if locality:
                    location = str(locality).strip()

            if not company and not location and not url:
                continue

            job = {
                "title": title,
                "company": company or "Unknown company",
                "location": location,
                "description_raw": str(node.get("description") or node.get("summary") or "").strip(),
            }
            if url:
                job["url"] = self._normalize_url(url)

            posted = node.get("datePosted") or node.get("postedAt")
            if posted:
                job["posted_at"] = posted

            jobs.append(job)
        return jobs

    def _extract_jobs_from_links(self, soup: BeautifulSoup) -> List[Dict]:
        jobs: List[Dict] = []
        links = soup.find_all("a", href=True)
        for link in links:
            href = str(link.get("href", ""))
            if "/job/" not in href.lower():
                continue
            title = link.get_text(" ", strip=True)
            if len(title) < 3:
                continue

            parent_text = ""
            parent = link.parent
            if parent:
                parent_text = parent.get_text(" ", strip=True)

            company = ""
            at_match = re.search(r"\bat\s+([A-Za-z0-9&.,' -]{2,80})", parent_text)
            if at_match:
                company = at_match.group(1).strip()

            jobs.append(
                {
                    "title": title,
                    "company": company or "Unknown company",
                    "url": self._normalize_url(href),
                    "description_raw": parent_text[:600],
                }
            )
        return jobs

    def _normalize_url(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.base_url + url
        return self.base_url + "/" + url
    
    def extract_job_data_from_card(self, card, page_number: int) -> Optional[Dict]:
        """Extract individual job data from a card element"""
        try:
            job = {}
            
            # Extract URL
            link = card.find('a', href=True)
            if link and link.get('href'):
                job['url'] = self._normalize_url(str(link.get('href')))
            
            # Extract title
            title_elem = (
                card.select_one('[data-at*="job-title"]')
                or card.select_one('[data-testid*="job-title"]')
                or card.find('h2')
                or card.find('h3')
            )
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    job['title'] = title
            if not job.get('title') and link:
                title = link.get_text(" ", strip=True)
                if title:
                    job["title"] = title
            
            # Extract company
            company_elem = (
                card.find('div', class_=lambda x: x and ('company' in str(x).lower() or 'res-frpqw3' in str(x)))
                or card.find('span', class_=lambda x: x and ('employer' in str(x).lower() or 'company' in str(x).lower()))
                or card.select_one('[data-at*="company"]')
                or card.select_one('[data-testid*="company"]')
            )
            if company_elem:
                company = company_elem.get_text(strip=True)
                if company:
                    job['company'] = company
            if not job.get("company"):
                text_blob = card.get_text(" ", strip=True)
                at_match = re.search(r"\bat\s+([A-Za-z0-9&.,' -]{2,80})", text_blob)
                if at_match:
                    job["company"] = at_match.group(1).strip()
            
            # Extract location
            location_elem = (
                card.find('div', class_=lambda x: x and ('location' in str(x).lower() or 'res-12jlzgf' in str(x)))
                or card.find('span', class_=lambda x: x and 'location' in str(x).lower())
                or card.select_one('[data-at*="location"]')
            )
            if location_elem:
                location = location_elem.get_text(strip=True)
                if location:
                    job['location'] = location
            
            # Extract salary
            salary_elem = card.find('div', class_=lambda x: x and ('salary' in str(x).lower() or 'res-5zx6ot' in str(x)))
            if salary_elem:
                salary = salary_elem.get_text(strip=True)
                if salary:
                    job['salary_raw'] = salary
            
            # Extract description
            desc_elem = card.find('div', {'data-at': 'jobcard-content'})
            if not desc_elem:
                desc_elem = card.find('div', class_=lambda x: x and ('description' in str(x).lower() or 'content' in str(x).lower()))
            if not desc_elem:
                desc_elem = card.find('p')
            if desc_elem:
                job['description_raw'] = desc_elem.get_text(" ", strip=True)
            
            # Extract posted date
            date_elem = card.find('time')
            if date_elem:
                if date_elem.get('datetime'):
                    job['posted_at'] = date_elem.get('datetime')
                else:
                    job['posted_at'] = date_elem.get_text(strip=True)

            if not job.get("company"):
                job["company"] = "Unknown company"
            
            return job
                
        except Exception as e:
            logger.debug(f"Error in extract_job_data: {e}")
            return None
