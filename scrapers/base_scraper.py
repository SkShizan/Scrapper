from abc import ABC, abstractmethod

class BaseScraper(ABC):
    @abstractmethod
    def search(self, query, location, api_key=None, cx=None):
        """
        Abstract method that all scrapers must implement.
        Must return a list of dictionaries:
        [{'Name': '...', 'Email': '...', 'Website': '...', 'Location': '...', 'Source': '...'}]
        """
        pass