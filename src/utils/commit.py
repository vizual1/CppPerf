import logging, json, csv
from pathlib import Path
from github.Commit import Commit

class CommitHandler:
    def __init__(self, input_file: str, output_path: str):
        self.input_file = input_file
        self.output_path = output_path

    def _get_commits_from_json_files(self) -> list[tuple[str, str, str]]:
        """
        Return list of (repo_id, new_sha, old_sha) pairs from
        json files generated from '--testcommits' flag. 
        """
        commits_info: list[tuple[str, str, str]] = []
        json_folder = Path(self.input_file)
        for json_file in json_folder.glob("*.json"):
            with open(json_file, 'r', errors='ignore') as f:
                res = json.load(f)

            metadata = res['metadata']
            commit_info = res['commit_info']
            repo_id = metadata['repository_name']
            new_sha = commit_info['new_sha']
            old_sha = commit_info['old_sha']
            commits_info.append((repo_id, new_sha.strip(), old_sha.strip()))
        
        return commits_info
    
    def get_commits(self, commits_list: list[tuple[str, Commit]] = []) -> list[tuple[str, str, str]]:
        """Return list of (repo_id, new_sha, old_sha) pairs."""
        file_path = Path(self.input_file)
        if commits_list:
            all_commits = [(repo_id, commit.sha, commit.parents[0].sha) for repo_id, commit in commits_list if commit is not None]
        elif file_path.is_file():
            all_commits = self._get_filtered_commits(file_path)
        elif file_path.is_dir():
            all_commits = self._get_commits_from_json_files()

        if not all_commits:
            logging.warning(f"No valid commit pairs found in {file_path}")

        return all_commits
    
    def get_paths(self, file_prefix: str, sha: str) -> tuple[Path, Path]:
        """
        Returns paths for {old,new} commit directories to be tested.
        Example: data/commits/<file_prefix>_<sha>/{old,new}
        """
        output = Path(self.output_path)
        if not output.exists():
            output.mkdir(exist_ok=True)
        commit_root = output / f"{file_prefix}_{sha}"
        old_path = commit_root / "old"
        new_path = commit_root / "new"
        return new_path, old_path
    
    def _get_filtered_commits(self, path: Path) -> list[tuple[str, str, str]]:
        commits_info: list[tuple[str, str, str]] = []

        if not path.exists():
            logging.warning(f"Commit file not found: {path}")
            return commits_info

        try:
            suffix = path.suffix.lower()

            if suffix == ".csv":
                return self._get_filtered_commits_csv(path)

            elif suffix == ".json":
                return self._get_filtered_commits_json(path)

            else:
                logging.warning(f"Unsupported file type '{suffix}' for {path}")
                return commits_info

        except Exception as e:
            logging.error(f"Failed to read commits from {path}: {e}", exc_info=True)
            return commits_info
        

    def _get_filtered_commits_csv(self, path: Path) -> list[tuple[str, str, str]]:
        commits_info: list[tuple[str, str, str]] = []

        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)

                required = {"repo", "patched_sha", "original_sha"}
                if not reader.fieldnames or not required.issubset(reader.fieldnames):
                    raise ValueError(
                        f"{path} missing required columns {required}, found {reader.fieldnames}"
                    )

                for i, row in enumerate(reader, start=2):
                    try:
                        repo_id = (row.get("repo") or "").strip()
                        new_sha = (row.get("patched_sha") or "").strip()
                        old_sha = (row.get("original_sha") or "").strip()

                        if not repo_id or not new_sha or not old_sha:
                            logging.warning(f"Incomplete row at {path}:{i} -> {row}")
                            continue

                        commits_info.append((repo_id, new_sha, old_sha))

                    except Exception as e:
                        logging.warning(f"Error parsing row {i} in {path}: {e}")
                        continue

        except (OSError, IOError) as e:
            logging.error(f"Failed to read CSV commits from {path}: {e}", exc_info=True)

        return commits_info
    
    def _get_filtered_commits_json(self, path: Path) -> list[tuple[str, str, str]]:
        commits_info: list[tuple[str, str, str]] = []

        with open(path, 'r', errors='ignore') as f:
            res = json.load(f)

        metadata = res['metadata']
        commit_info = res['commit_info']
        repo_id = metadata['repository_name']
        new_sha = commit_info['new_sha']
        old_sha = commit_info['old_sha']
        commits_info.append((repo_id, new_sha.strip(), old_sha.strip()))
        
        return commits_info

    def get_file_prefix(self, repo_id: str) -> str:
        try:
            owner, name = repo_id.strip().split("/", 1)
        except ValueError:
            raise ValueError(f"Invalid repo ID format: '{repo_id}'. Expected '<owner>/<repo>'.")
        
        return f"{owner}_{name}"