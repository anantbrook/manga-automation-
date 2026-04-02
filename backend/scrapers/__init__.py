from .mangadex import MangaDexScraper
from .aquareader import AquaReaderScraper

# Factory mapping
scrapers = {
    'mangadex': MangaDexScraper(),
    'aquareader': AquaReaderScraper()
}

def get_scraper(source='mangadex'):
    return scrapers.get(source, scrapers['mangadex'])