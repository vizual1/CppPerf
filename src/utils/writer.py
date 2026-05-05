import logging, json, fcntl, os, csv
from github.Repository import Repository
from github.Commit import Commit
from src.utils.stats import CommitStats
from typing import Optional
from pathlib import Path
from src.utils.pull_request_handler import get_pr_chain_msg

class Writer:
    def __init__(self, repo_id: str, output_path: str):
        self.repo_id = repo_id
        try:
            self.owner, self.name = self.repo_id.split("/", 1)
        except ValueError:
            raise ValueError(f"Invalid repo name format: '{repo_id}'. Expected '<owner>/<repo>'.")
        
        self.output_path = output_path
        self.file: Optional[str] = None

    def write_repo(self) -> None:
        #msg = " | ".join([f"{self.owner}/{self.name}"])
        #msg += f"\n"
        path = Path(self.output_path)
        #self._write(path, msg)
        self._write_csv(path, row=[f"{self.owner}/{self.name}"], header=["repo"])

    def write_commit(self, commit: Commit, filter: str) -> CommitStats:
        stats = CommitStats()

        stats.perf_commits += 1
        total_add = sum(f.additions for f in commit.files)
        total_del = sum(f.deletions for f in commit.files)

        stats.lines_added += total_add
        stats.lines_deleted += total_del

        current_sha: str = commit.sha
        parent_sha: str = commit.parents[0].sha if commit.parents else "None"

        self.file = "filtered.csv"
        #msg = f"{self.repo_id} | {current_sha} | {parent_sha}\n" 
        path = Path(self.output_path) / self.file
        #self._write(path, msg)
        self._write_csv(path, row=[self.repo_id, current_sha, parent_sha], header=["repo", "patched_sha", "original_sha"])

        return stats
    
    def write_pr_commit(self, repo: Repository, commit: Commit, is_issue: bool):
        stats = CommitStats()

        stats.perf_commits += 1
        total_add = sum(f.additions for f in commit.files)
        total_del = sum(f.deletions for f in commit.files)

        stats.lines_added += total_add
        stats.lines_deleted += total_del

        repo_id, current_sha, parent_sha = get_pr_chain_msg(repo, commit, is_issue)
        path = Path(self.output_path)
        #self._write(path, msg)
        self._write_csv(path, row=[self.repo_id, current_sha, parent_sha], header=["repo", "patched_sha", "original_sha"])

        return stats

    def write_improve(self, results: dict) -> None:
        self.file = f"improved.csv"
        path = Path(self.output_path) / self.file
        current_sha: str = results['commit_info']["new_sha"]
        parent_sha: str = results['commit_info']["old_sha"]
        repo_id: str = results['metadata']['repository_name']
        #msg = f"{repo_id} | {new_sha} | {old_sha}\n"
        #self._write(path, msg)
        self._write_csv(path, row=[self.repo_id, current_sha, parent_sha], header=["repo", "patched_sha", "original_sha"])


    def write_results(self, results: dict) -> None:
        new_sha: str = results['commit_info']["new_sha"]
        file = f"{self.owner}_{self.name}_{new_sha}.json"
        path = Path(self.output_path) / file
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logging.info(f"[{self.owner}/{self.name}] Wrote results to {path}")

    
    def _write(self, path: Path, msg: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "a", encoding="utf-8", errors="ignore") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(msg)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)

    def _write_csv(self, path: Path, row: list[str], header: Optional[list[str]] = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = path.exists()
        with open(path, "a", encoding="utf-8", newline="") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            writer = csv.writer(f)
            if header and (not file_exists or path.stat().st_size == 0):
                writer.writerow(header)
            writer.writerow(row)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f, fcntl.LOCK_UN)