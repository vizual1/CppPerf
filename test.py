import subprocess, sys, csv
from pathlib import Path

CWD = Path(__file__).parent
PYTHON_EXEC = sys.executable

def test_collect():
    cmd = [PYTHON_EXEC, "main.py", "discover", "--repos=3", "--stars=1000"]
    subprocess.run(cmd, check=True, cwd=CWD)

    collect = Path("data/collect.csv")
    with open(collect, 'r') as f:
        reader = csv.DictReader(f)
        repos = [row["repo"].strip() for row in reader if row.get("repo")]
    assert len(repos) == 3
    print("TEST (discover repository) SUCCESSFUL")
    collect.unlink(True)
    
    discover = Path("data/discovered.csv")
    with open(discover, 'r') as f:
        reader = csv.DictReader(f)
        repos = [row["repo"].strip() for row in reader if row.get("repo")]
    assert len(repos) >= 3
    discover.unlink(True)

    cmd = [PYTHON_EXEC, "main.py", "validate", "--repositories", "--input=data/test/test_repositories.csv"]
    subprocess.run(cmd, check=True, cwd=CWD)

    testcollect = Path("data/collect.csv")
    if testcollect.exists():
        with open(testcollect, 'r') as f:
            reader = csv.DictReader(f)
            repos = [row["repo"].strip() for row in reader if row.get("repo")]
    else:
        repos = []
    assert len(repos) >= 1
    print("TEST (validate repository) SUCCESSFUL")
    testcollect.unlink(True)

def test_commits():
    cmd = [PYTHON_EXEC, "main.py", "discover", "--filter=simple", "--input=data/test/test_repositories.csv", "--limit=3"]
    subprocess.run(cmd, check=True, cwd=CWD)

    filtered_commits = Path("data/filtered_commits.csv")
    assert filtered_commits.exists()
    print("TEST (discover commits) SUCCESSFUL")
    filtered_commits.unlink()

    cmd = [PYTHON_EXEC, "main.py", "discover", "--test", "--filter=simple", "--input=data/test/test_repositories.csv", "--limit=3"]
    subprocess.run(cmd, check=True, cwd=CWD)

    filtered_commits = Path("data/filtered_commits.csv")
    assert filtered_commits.exists()
    print("TEST (discover commits + tests) 1 SUCCESSFUL")
    filtered_commits.unlink()

    json_files = list(Path("data/commits/").glob("*.json"))
    assert json_files
    assert len(json_files) == 3
    for file in json_files:
        file.unlink()
    print("TEST (discover commits + tests) 2 SUCCESSFUL")

    cmd = [PYTHON_EXEC, "main.py", "validate", "--commits", "--input=data/test/test_commits.csv"]
    subprocess.run(cmd, check=True, cwd=CWD)

    json_files = list(Path("data/commits/").glob("*.json"))
    assert json_files
    assert len(json_files) == 2
    for file in json_files:
        file.unlink()
    print("TEST (validate commits) SUCCESSFUL")

def test_docker():
    image = "madmann91_bvh_1b2472a44e22fcf7dc921b7eb36b7729ec97e8b5"
    cmd = [PYTHON_EXEC, "main.py", "artifact", "--generate", f"--input=data/test/"]
    subprocess.run(cmd, check=True, cwd=CWD)

    cmd = ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=CWD)
    images = result.stdout.strip().split("\n")
    assert f"{image}:latest" in images
    print("TEST (artifact generate docker image) SUCCESSFUL")

    cmd = [PYTHON_EXEC, "main.py", "benchmark", f"--docker={image}"]
    subprocess.run(cmd, check=True, cwd=CWD)

    json_files = list(Path("data/commits/").glob("*.json"))
    assert json_files and len(json_files) == 1
    json_tests = list(j.stem for j in Path("data/test/").glob("*.json"))
    for file in json_files:
        assert file.stem in json_tests
        assert f"{file.stem}:latest" in images
        cmd = ["docker", "rmi", image]
        subprocess.run(cmd, check=True, cwd=CWD)
        file.unlink()
    print("TEST (benchmark docker) 1 SUCCESSFUL")

    cmd = [PYTHON_EXEC, "main.py", "artifact", "--pull", f"--input=data/test/"]
    subprocess.run(cmd, check=True, cwd=CWD)
    cmd = ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=CWD)
    images = result.stdout.strip().split("\n")
    assert f"{image}:latest" in images
    print("TEST (aritfact pull docker images) SUCCESSFUL")

    cmd = [PYTHON_EXEC, "main.py", "benchmark", f"--docker={image}"]
    subprocess.run(cmd, check=True, cwd=CWD)

    json_files = list(Path("data/commits/").glob("*.json"))
    assert json_files
    json_tests = list(j.stem for j in Path("data/test/").glob("*.json"))
    for file in json_files:
        assert file.stem in json_tests
        assert f"{file.stem}:latest" in images
        file.unlink()
    print("TEST (benchmark docker) 2 SUCCESSFUL")

    cmd = [PYTHON_EXEC, "main.py", "benchmark", f"--docker={image}", f"--diff=data/test/{image}.patch"]
    subprocess.run(cmd, check=True, cwd=CWD)
    json_files = list(Path("data/commits/").glob("*.json"))
    assert json_files
    json_tests = list(j.stem for j in Path("data/test/").glob("*.json"))
    for file in json_files:
        assert file.stem in json_tests
        cmd = ["docker", "rmi", image, f"tommyho1999/opt-repo-cpp:{image}"]
        subprocess.run(cmd, check=True, cwd=CWD)
        file.unlink()
    print("TEST (benchmark patch) SUCCESSFUL")

def test_llm():
    cmd = [PYTHON_EXEC, "main.py", "discover", "--filter=llm", "--input=data/test/test_repositories.txt", "--limit=3"]
    subprocess.run(cmd, check=True, cwd=CWD)

    
def main() -> None:
    test_collect()
    test_commits()
    test_docker()
    #test_llm()

if __name__ == '__main__':
    main()
