# CppPerf: Automatic C++ Performance-Optimization Commits Mining Pipeline

CppPerf is an automatic pipeline to collect performance-optimization commits from GitHub. The pipeline mines repositories from GitHub, identifies candidate performance-optimizing commits from the collected repositories, builds and executes the commits in Docker environments, performs statistical performance evaluation on the execution results, and stores the commits in Docker images and results in json files.

---

## Features

- Automated repository collection from GitHub
- LLM-based commit classification from commit data
- Automated build and testing of commits in a Docker execution environment
- Statistical performance evaluation of testing measurements
- Stored results in reproducible Docker images and json files

---

## Overview

The pipeline performs the following steps:

1. Repository collection from GitHub
2. Structural commit filtering from GitHub repositories
3. LLM-based classification of commits
4. Containerized build and test execution
5. Statistical runtime analysis
6. Reproducible dataset generation

---

## Prerequisites

### Environment Setup
1. **Configure environment variables** in ```.env```

2. **Install Python dependencies**:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Build Docker images** for different C++ versions:
```bash
docker build -t cpp20 -f docker/Dockerfile.20.04 .
docker build -t cpp22 -f docker/Dockerfile.22.04 .
docker build -t cpp24 -f docker/Dockerfile.24.04 .
```

---

# Running
1. **Collecting Repositories**
Use ```discover``` to mine GitHub for C++ repositories:
```bash
# Collect and structurally validate (most recent commit): 
# 10 repos (min 20 stars, max 1000 stars)
python3 main.py discover --repos=10 --stars=1000

# Collect, structurally validate, and build and test (most recent commit)
python3 main.py discover --repos=10 --stars=1000 --test

# Structurally validate, and build and test (most recent commit)
python3 main.py validate --repositories --input=data/collect.csv
```

*Outputs*
- ```data/collect.csv``` - Validated collection results (owner/repo per line)
- ```data/fail.csv``` - Repositories that failed validation (owner/repo per line)

2. **Collecting and Testing Commits**
LLM filtering currently supports Ollama, OpenAI, and OpenRouter APIs. The default model configuration is defined in ```config/config.yaml```. 

Filter commits from collected repositories:
```bash
# Collect and filter commits with LLM
python3 main.py discover --filter=llm --input=data/collect.csv

# Collect and filter commits, then build and test commits
python3 main.py discover --test --filter=llm --input=data/collect.csv

# Build and test commits
python3 main.py validate --commits --input=data/filtered_commits.csv
```

*Outputs*:
- ```data/filtered_commits.csv``` - filtered commits (```owner/repo,newsha,oldsha``` per line)
- ```data/commits/owner_repo_newsha.json``` - multiple JSON files of built and tests commits, containing:
    - Build and test commands executed
    - Execution times
    - Statistical analysis

3. **Docker Operations**
```bash
# Test a specific Docker image
python main.py benchmark --docker=<owner_repo_newsha>

# Generate Docker images without testing of collected commits from a folder of JSON files
python main.py artifact --generate --input=data/dataset/

# Test a patch from a diff file (the diff file is applied to /test_workspace/workspace/old)
python main.py benchmark --docker=<owner_repo_newsha> --diff=/path/to/diff.patch
```

*Outputs*:
- ```data/commits/owner_repo_newsha.json``` - multiple JSON files of built and tests commits, containing:
    - Build and test commands executed
    - Execution times
    - Statistical analysis

4. **Inspect Results**
```bash
# inspect a generated result json file
python main.py inspect --input=path/to/json_file

# result json file needs to be in data/commits/
python main.py inspect --id=<owner_repo_newsha>
python main.py inspect --repo=<owner_repo> --sha=<newsha>
```

---

## Artifacts and Dataset

Dataset Docker images:
```bash
# set in .env
# DOCKER_HUB_USER=tommyho1999
# DOCKER_HUB_REPO=opt-repo-cpp

# Pulls Docker images from Dockerhub of collected commits from a folder of JSON files
# WARNING: This command downloads the entire dataset of Docker images (347)
python main.py artifact --pull --input=data/dataset/

# or run for a single Docker image
python main.py artifact --pull --input=data/dataset/<owner_repo_newsha>.json 
```
Note: Prebuilt Docker images are available on
[DockerHub](https://hub.docker.com/repository/docker/tommyho1999/opt-repo-cpp)

Results are in:
```
├── data/
│   └── dataset/                       # Final dataset test results
│   └── patch/                         # OpenHands (gpt-5-mini) generated patches on the dataset
│   └── significant/                   # Dataset with statistical significant test results
│   └── llm_qwen_filter_eval.csv       # Manual annotations of LLM-filtered commits
│   └── openhands_patch_comparison.csv # Manual comparisons of openhands patches to ground-truth
```

---

## Project Structure
```
├── main.py                  # Main entry point
├── src/                     # Source code
│   ├── core/                # Core functionality
│   └── config/              # Configuration handling
│       └── config.py        # Main project configuration file
│       └── settings.py      # LLM, test, resource settings
├── data/                    # Output directory
│   ├── collect.txt          # Collected repositories
│   ├── testcollect.txt      # Validated repositories
│   ├── fail.txt             # Failed repositories
│   ├── filtered_commits.txt # Filtered commits
│   └── commits/             # Individual commit test results
└── docker/                  # Docker configuration files
```

---

## Docker Container Structure
When running tests in Docker, the container has the following structure:
- ```/test_workspace/workspace/old``` - Original commit
- ```/test_workspace/workspace/new``` - Patched commit
- ```/test_workspace/old_build.sh```  - Original build script
- ```/test_workspace/new_build.sh```  - Patched build script
- ```/test_workspace/old_test.sh```   - Original test script
- ```/test_workspace/new_test.sh```   - Patched test script

---

## Testing
Run a minimal pipeline test:
```bash
python3 test.py
```