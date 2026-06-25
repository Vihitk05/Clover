from scraper.spiders.jobsie import JobsIEDirectSpider
from config.settings import config


class IrishJobsDirectSpider(JobsIEDirectSpider):
    """Direct scraper variant for IrishJobs.ie using the Jobs.ie parser heuristics."""

    def __init__(self):
        super().__init__()
        self.source_name = "irishjobs.ie"
        self.base_url = config.IRISH_JOBS_BASE_URL
        self.search_url = config.IRISH_JOBS_SEARCH_URL
