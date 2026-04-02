from app.scraper.aquareader import AquaReaderScraper
from app.scraper.asura import AsuraScansScraper
from app.scraper.mangadex import MangaDexScraper
from app.scraper.manganato import ManganatoScraper
from app.core.logger import logger

class ScraperFactory:
    _scrapers = [
        AquaReaderScraper(),
        AsuraScansScraper(),
        MangaDexScraper(),
        ManganatoScraper()
    ]

    @classmethod
    def get_scraper_by_url(cls, url):
        for scraper in cls._scrapers:
            if scraper.is_supported(url):
                return scraper
        logger.warning(f"No scraper found for URL: {url}")
        return None

    @classmethod
    def get_scraper_by_source(cls, source):
        for scraper in cls._scrapers:
            if scraper.__class__.__name__.lower().startswith(source.lower()):
                return scraper
        return None
