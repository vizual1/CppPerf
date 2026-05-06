import json
from pathlib import Path

def inspect_result(repo: str, newsha: str, data_dir: str = "data/commits"):
    path = Path(data_dir)
    if not data_dir.endswith(".json"):
        repo_safe = repo.replace("/", "_")
        filename = f"{repo_safe}_{newsha}.json"
        path = Path(data_dir) / filename

    if not path.exists() and not path.is_file():
        raise FileNotFoundError(f"Result not found: {path}")

    with open(path, "r") as f:
        data = json.load(f)

    commit = data["commit_info"]
    perf = data["performance_analysis"]
    tests = data["tests"]
    logs = data["logs"]

    print("\n================ BENCHMARK INSPECTION ================\n")

    print(f"[Performance] {repo}")
    print(f"Commit: {commit['old_sha']} → {commit['new_sha']}")
    print(f"Date: {commit['commit_date']}\n")

    files = commit["files_changed"]
    print(f"Changed files ({len(files)}):")
    for f in files[:10]:
        print(f"  - {f['filename']}")
    if len(files) > 10:
        print("  ...")

    print("\n---------------- BUILD / TEST ----------------")
    print(f"Build: {'SUCCESS' if logs['build_success'] else 'FAIL'}")
    print(f"Tests: {'PASS' if logs['test_success'] else 'FAIL'}")
    print(f"Test Runtime: {logs.get('test_runtime', 0.0):.2f}s")

    print("\n---------------- PERFORMANCE ----------------")
    print(f"Runtime Improvement: {perf['relative_improvement']*100:.3f}%")
    print(f"Effect size (Cohen's d): {perf['effect_size_cohens_d']:.3f}")
    print(f"p-value: {perf['pair_p_value']:.6f}")

    sig = "YES" if perf["is_pair_significant"] else "NO"
    print(f"Statistically significant: {sig}")

    print("\n---------------- TEST SUMMARY ----------------")
    print(f"Total tests: {tests['total_tests']}")
    print(f"Significant Regressions: {tests['significant_pair_regressions']}")
    print(f"Significant Improvements: {tests['significant_pair_improvements']}")
    significant_tests = tests['significant_pair_improvements_tests']
    print(f"Tests with Significant Runtime Improvements:")
    for f in significant_tests[:10]:
        print(f"  - {f}")
    if len(files) > 10:
        print("  ...")

    print("\n======================================================\n")