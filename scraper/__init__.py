# Lazy imports to avoid forcing apify-client at package level
__all__ = ['IndeedSpider', 'LinkedInSpider']


def __getattr__(name):
    if name == 'IndeedSpider':
        from scraper.spiders.indeed import IndeedSpider
        return IndeedSpider
    if name == 'LinkedInSpider':
        from scraper.spiders.linkedin import LinkedInSpider
        return LinkedInSpider
    raise AttributeError(f"module 'scraper' has no attribute {name!r}")