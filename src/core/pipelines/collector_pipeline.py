import logging
from src.config.config import Config
from src.gh.collector import RepositoryCollector
from github.Repository import Repository

class CollectionPipeline:
    """
    This class collects popular GitHub repositories.
    """
    def __init__(self, config: Config):
        self.config = config

    def query_popular_repos(self) -> list[Repository]:
        collector = RepositoryCollector(config=self.config)
        repos = collector.query_popular_repos()
        logging.info(f"Found {len(repos)} repositories from collector.")
        return repos