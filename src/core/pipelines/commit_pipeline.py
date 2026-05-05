import logging
from tqdm import tqdm
from src.config.config import Config
from src.utils.writer import Writer
from src.core.filter.commit_filter import CommitFilter
from src.utils.stats import CommitStats
from github.Repository import Repository
from github.Commit import Commit

class CommitPipeline:
    """
    This class filters and saves the commit history of a repository.
    """
    def __init__(self, repo_ids: list[str], config: Config):
        self.config = config
        self.repo_ids = repo_ids
        self.stats = CommitStats()
        self.filtered_commits: list[tuple[str, Commit]] = []

    def filter_all_commits(self):
        for repo_id in self.repo_ids:
            repo = self.config.git_client.get_repo(repo_id)

            since = self.config.commits_time['since']
            until = self.config.commits_time['until']
            try:
                self.commits = repo.get_commits(sha=repo.default_branch, since=since, until=until)
            except Exception as e:
                logging.exception(f"[{repo.full_name}] Error fetching commits: {e}")
                self.commits = []
            limit = "all" if self.config.discover.limit == -1 else self.config.discover.limit
            logging.info(f"Filtering {limit} commits in {repo.full_name}")
            self.filter_commits_from_repo(repo)

    def filter_commits_from_repo(self, repo: Repository) -> None:
        if not self.commits:
            logging.warning(f"[{repo.full_name}] No commits found")
            return
        
        stats = CommitStats()
        for commit in tqdm(self.commits, desc=f"{repo.full_name} commits", position=1, leave=False, mininterval=5):
            if self.config.discover.limit != -1 and len(self.filtered_commits) >= self.config.discover.limit:
                break

            stats.num_commits += 1
            perf_improv_filter = CommitFilter(repo, commit, self.config)
            if not perf_improv_filter.accept():
                continue
            
            self.filtered_commits.append((repo.full_name, commit))
            writer = Writer(repo.full_name, self.config.output or self.config.storage_paths['commits'])
            stats.perf_commits += 1
            stats += writer.write_pr_commit(repo, commit, perf_improv_filter.is_issue)

        stats.write_final_log()
