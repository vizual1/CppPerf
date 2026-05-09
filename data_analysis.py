from __future__ import annotations

import json
import os
import time
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATASET_DIR = Path("data/dataset")
TOKEN_ENV_VAR = "github_access_token"


@dataclass(frozen=True)
class RepoMetrics:
    stars: int
    commits: int


def _read_repo_name_from_json(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        return None

    repo_name = metadata.get("repository_name")
    if not isinstance(repo_name, str) or not repo_name.strip():
        return None

    # normalize: accept either full URL or owner/repo
    repo_name = repo_name.strip()
    if repo_name.startswith("https://github.com/"):
        repo_name = repo_name.removeprefix("https://github.com/").strip("/")

    return repo_name or None


def _get_repo_metrics(
    gh: Any,
    repo_full_name: str,
    cache: dict[str, RepoMetrics],
) -> RepoMetrics | None:
    repo_full_name = repo_full_name.strip().strip("/")
    if not repo_full_name:
        return None

    cached = cache.get(repo_full_name)
    if cached is not None:
        return cached

    while True:
        try:
            repo = gh.get_repo(repo_full_name)
            stars = int(repo.stargazers_count)
            commits = int(repo.get_commits().totalCount)
            metrics = RepoMetrics(stars=stars, commits=commits)
            cache[repo_full_name] = metrics
            return metrics
        except Exception as e:
            print(f"Error getting metrics for {repo_full_name}: {e}")
            return None


def _five_number_summary(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": float("nan"), "Q1": float("nan"), "median": float("nan"), "Q3": float("nan"), "max": float("nan")}

    xs = sorted(float(v) for v in values)

    def percentile_linear(p: float) -> float:
        if p <= 0.0:
            return xs[0]
        if p >= 1.0:
            return xs[-1]
        n = len(xs)
        idx = (n - 1) * p
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return xs[lo] + (xs[hi] - xs[lo]) * frac

    return {
        "min": percentile_linear(0.0),
        "Q1": percentile_linear(0.25),
        "median": percentile_linear(0.5),
        "Q3": percentile_linear(0.75),
        "max": percentile_linear(1.0),
    }


def compute_commits_stars() -> None:
    try:
        from github import Github  # type: ignore[import-not-found]
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "PyGithub is not installed in this environment. "
            "Install it (pip install PyGithub) or run this on an environment with project dependencies."
        ) from e

    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise RuntimeError(f"Missing GitHub token in environment variable {TOKEN_ENV_VAR!r}")

    dataset_dir = DATASET_DIR
    if not dataset_dir.is_dir():
        raise RuntimeError(f"Dataset directory not found: {dataset_dir}")

    gh = Github(token)

    json_paths = sorted(dataset_dir.glob("*.json"))
    repo_names: list[str] = []
    for p in json_paths:
        repo_name = _read_repo_name_from_json(p)
        if repo_name:
            repo_names.append(repo_name)

    cache: dict[str, RepoMetrics] = {}
    stars: list[int] = []
    commits: list[int] = []

    for repo_name in repo_names:
        metrics = _get_repo_metrics(gh, repo_name, cache)
        if metrics is None:
            continue
        stars.append(metrics.stars)
        commits.append(metrics.commits)

    print(f"dataset_json_files: {len(json_paths)}")
    print(f"repos_seen_in_json: {len(repo_names)}")
    print(f"unique_repos: {len(set(repo_names))}")
    print(f"repos_fetched_successfully: {len(stars)}")
    print()
    print("stars_summary:", _five_number_summary(stars))
    print("commits_summary:", _five_number_summary(commits))


def compute_change_scale() -> None:
    """
    Count dataset JSON files with multi-file changes and summarize change sizes.

    Multi-file change is defined as commit_info.files_changed having length > 1.
    Change size is derived from the per-file "changes" field and aggregated per JSON
    as total changed lines across all changed files in that commit.
    """
    dataset_dir = DATASET_DIR
    if not dataset_dir.is_dir():
        raise RuntimeError(f"Dataset directory not found: {dataset_dir}")

    json_paths = sorted(dataset_dir.glob("*.json"))
    multi_file_count = 0
    single_file_count = 0
    changed_lines_all: list[int] = []

    for path in json_paths:
        try:
            with path.open("r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        commit_info = data.get("commit_info")
        if not isinstance(commit_info, dict):
            continue

        files_changed = commit_info.get("files_changed")
        if not isinstance(files_changed, list) or not files_changed:
            continue

        total_changes = 0
        for fc in files_changed:
            if not isinstance(fc, dict):
                continue
            changes = fc.get("changes")
            if isinstance(changes, (int, float)):
                total_changes += int(changes)

        if len(files_changed) > 1:
            multi_file_count += 1
        else:
            single_file_count += 1
        changed_lines_all.append(total_changes)

    print(f"dataset_json_files: {len(json_paths)}")
    print(f"multi_file_change_files: {multi_file_count}")
    print(f"single_file_change_files: {single_file_count}")
    print("changed_lines_summary_all_commits:", _five_number_summary(changed_lines_all))

def compute_openhands_res() -> None:
    dataset_dir = DATASET_DIR
    if not dataset_dir.is_dir():
        raise RuntimeError(f"Dataset directory not found: {dataset_dir}")

    csv_path = Path("data/openhands_patch_comparison.csv")
    if not csv_path.is_file():
        raise RuntimeError(f"OpenHands comparison CSV not found: {csv_path}")

    # Map commit SHA -> is_multi_file (True if files_changed length > 1)
    sha_to_is_multi: dict[str, bool] = {}
    json_paths = sorted(dataset_dir.glob("*.json"))
    for path in json_paths:
        try:
            with path.open("r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        commit_info = data.get("commit_info")
        if not isinstance(commit_info, dict):
            continue

        sha = commit_info.get("new_sha")
        if not isinstance(sha, str) or not sha:
            continue

        files_changed = commit_info.get("files_changed")
        if not isinstance(files_changed, list) or not files_changed:
            continue

        sha_to_is_multi[sha] = len(files_changed) > 1

    def extract_sha_from_commit_url(url: str) -> str | None:
        url = url.strip()
        if not url:
            return None
        # Expected: https://github.com/<owner>/<repo>/commit/<sha>
        parts = url.strip("/").split("/")
        if not parts:
            return None
        sha = parts[-1]
        if len(sha) < 7:
            return None
        return sha

    all_counts: Counter[str] = Counter()
    single_counts: Counter[str] = Counter()
    multi_counts: Counter[str] = Counter()

    total_rows = 0
    matched_rows = 0
    missing_sha_rows = 0
    unmapped_sha_rows = 0

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or len(header) < 2:
            raise RuntimeError(f"Unexpected CSV format in {csv_path}")

        for row in reader:
            if not row or len(row) < 2:
                continue
            total_rows += 1
            label = (row[0] or "").strip()
            commit_url = (row[1] or "").strip()
            if not label or not commit_url:
                continue

            sha = extract_sha_from_commit_url(commit_url)
            if sha is None:
                missing_sha_rows += 1
                continue

            is_multi = sha_to_is_multi.get(sha)
            if is_multi is None:
                unmapped_sha_rows += 1
                continue

            matched_rows += 1
            all_counts[label] += 1
            if is_multi:
                multi_counts[label] += 1
            else:
                single_counts[label] += 1

    print(f"dataset_json_files: {len(json_paths)}")
    print(f"openhands_csv_rows: {total_rows}")
    print(f"openhands_rows_matched_to_dataset: {matched_rows}")
    print(f"openhands_rows_missing_sha: {missing_sha_rows}")
    print(f"openhands_rows_sha_not_in_dataset: {unmapped_sha_rows}")
    print()
    print("openhands_label_counts_all:", dict(all_counts))
    print("openhands_label_counts_single_file:", dict(single_counts))
    print("openhands_label_counts_multi_file:", dict(multi_counts))

def main() -> None:
    compute_openhands_res()

if __name__ == "__main__":
    main()
