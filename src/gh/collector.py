import logging, time, csv
from tqdm import tqdm
from datetime import datetime, timezone, timedelta
from pathlib import Path
from src.config.config import Config
from github.GithubException import GithubException, RateLimitExceededException
from github.Repository import Repository
from src.core.filter.structure_filter import StructureFilter
from src.core.filter.process_filter import ProcessFilter
from src.utils.writer import Writer
class RepositoryCollector:

    # languages considered acceptable alongside C++
    ACCEPTABLE_LANGUAGES = {
        "C++", "CMake", "Shell", "C", "Makefile", "Dockerfile",
        "Meson", "Bazel", "Ninja", "QMake", "Gradle", "JSON", "YAML",
        "TOML", "INI", "Batchfile", "PowerShell", "Markdown",
        "HTML", "CSS", "TeX"
    }
    MAX_OTHER_LANGUAGE_RATIO = 0.05
    STAR_REDUCTION_FACTOR = 0.95

    def __init__(self, config: Config, language: str = "C++"):
        self.language = language
        self.config = config

    def get_repos(self) -> list[str]:
        """Get repository IDs from input file or default location."""
        path = self.config.input or self.config.storage_paths["repos"]
        logging.debug(f"Loading repos from: {path}")
        return self._get_repo_ids(path)
    
    def query_popular_repos(self) -> list[Repository]:
        """
        Query GitHub for popular repositories matching criteria.
        
        Returns:
            List of Repository objects that match language and composition criteria
        """
        seen_repo_ids = set()
        if self.config.discover.blacklist and Path(self.config.discover.blacklist).is_file:
            seen_repo_ids = set(self._get_repo_ids(self.config.discover.blacklist))
            logging.info(f"Loaded {len(seen_repo_ids)} existing repositories to skip")

        results: list[Repository] = []
        limit = self.config.discover.repos
        count = 0

        logging.info(f"Starting GitHub query for popular {self.language} repos...")
        logging.info(f"Target: {limit} repos")

        start_boundary = self.config.commits_time['since']
        window_end = datetime.now(timezone.utc)
        window_size = timedelta(days=1)
            
        with tqdm(desc="Discovering repos", unit=" repos", mininterval=5) as pbar:
            while window_end > start_boundary and count < limit:
                window_start = max(start_boundary, window_end - window_size)
                pushed_range = f"pushed:{window_start.date()}..{window_end.date()}"
                query = f"{pushed_range} language:{self.language} archived:false"
                query += f" stars:{self.config.discover.min_stars}..{self.config.discover.stars}"
                    
                logging.info(f"Query: {query}")

                try:
                    repos = self.config.git_client.search_repositories(
                        query=query, sort="stars", order="desc"
                    )
                    for repo in repos:
                        if repo.full_name in seen_repo_ids:
                            logging.debug(f"Skipping {repo.full_name}: already in input list")
                            continue
                        Writer(repo.full_name, self.config.storage_paths['discovered']).write_repo()
                        if self._is_valid_repo(repo) and self.test_repo(repo):
                            results.append(repo)
                            Writer(repo.full_name, self.config.output or self.config.storage_paths['collect']).write_repo()
                            seen_repo_ids.add(repo.full_name)
                            count += 1
                            pbar.update(1)
                            pbar.set_postfix({"matched": count})

                            if count >= limit:
                                break
                        else:
                            Writer(repo.full_name, self.config.storage_paths['fail']).write_repo()

                        time.sleep(0.5)

                except RateLimitExceededException:
                    logging.warning("Rate limit exceeded. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                except GithubException as e:
                    logging.error(f"GitHub API error: {e}")
                    time.sleep(5)
                    continue

                window_end = window_start
            
        logging.info(f"Collected {len(results)} repositories matching criteria")
        return results
    
    def _is_valid_repo(self, repo: Repository) -> bool:
        """
        Check if repository meets language composition criteria.
        
        Args:
            repo: GitHub Repository object to validate
            
        Returns:
            True if repo has C++ and acceptable language composition
        """
        try:
            languages = repo.get_languages()
            cpp_bytes = languages.get("C++", 0)
            total_bytes = sum(languages.values())

            if total_bytes == 0 or cpp_bytes == 0:
                return False
            
            for lang, size in languages.items():
                if lang not in self.ACCEPTABLE_LANGUAGES:
                    ratio = size / total_bytes
                    if ratio > self.MAX_OTHER_LANGUAGE_RATIO:
                        logging.debug(
                            f"Rejecting {repo.full_name}: "
                            f"{lang} comprises {ratio:.1%} (threshold: {self.MAX_OTHER_LANGUAGE_RATIO:.1%})"
                        )
                        return False
            
            return True

        except GithubException as e:
            logging.warning(f"Error checking languages for {repo.full_name}: {e}")
            return False
        
    def test_repo(self, repo: Repository) -> bool:
        repo_id = repo.full_name
        structure = StructureFilter(self.config)
        process = ProcessFilter(self.config)
        try:
            if structure.is_valid(repo) and (not self.config.discover.test or process.valid_run("_".join(repo.full_name.split("/")), repo)):
                return True
        except Exception as e:
            logging.exception(f"[{repo_id}] Error processing repository: {e}")
        return False

    def _get_repo_ids(self, path: str) -> list[str]:
        repo_ids: list[str] = []

        try:
            file_path = Path(path)

            if not file_path.exists():
                logging.warning(f"Input file not found: {path}")
                return repo_ids

            if not file_path.is_file():
                logging.warning(f"Input path is not a file: {path}")
                return repo_ids

            with open(file_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)

                if not reader.fieldnames:
                    raise ValueError(f"CSV file has no header: {path}")

                # Prefer explicit schema
                if "repo" not in reader.fieldnames:
                    raise ValueError(f"CSV must contain a 'repo' column. Found: {reader.fieldnames}")

                for i, row in enumerate(reader, 2):  # header = line 1
                    try:
                        raw = (row.get("repo") or "").strip()
                        if not raw:
                            continue

                        repo_id = self._normalize_repo(raw)
                        if repo_id:
                            repo_ids.append(repo_id)

                    except Exception as e:
                        logging.warning(f"Error parsing row {i} in {path}: {e}")
                        continue

            logging.info(f"Loaded {len(repo_ids)} repository IDs from {path}")

        except (OSError, IOError) as e:
            logging.error(f"Failed to read repo list from {path}: {e}", exc_info=True)

        return repo_ids
    
    def _normalize_repo(self, raw: str) -> str:
        """
        Normalize a repository reference into 'owner/repo'.
        Accepts:
        - owner/repo
        - https://github.com/owner/repo
        """

        raw = raw.strip()

        if raw.startswith("https://github.com/"):
            raw = raw.removeprefix("https://github.com/")

        # Remove trailing slashes or .git
        raw = raw.rstrip("/")
        if raw.endswith(".git"):
            raw = raw[:-4]

        if "/" not in raw:
            raise ValueError(f"Invalid repo format: '{raw}'")

        owner, repo = raw.split("/", 1)
        if not owner or not repo:
            raise ValueError(f"Invalid repo format: '{raw}'")

        return f"{owner}/{repo}"