from dataclasses import dataclass
from dotenv import load_dotenv
import os

@dataclass
class EnvSettings:
    github_token: str
    llm_api_key: str
    dockerhub_user: str
    dockerhub_repo: str


def load_env() -> EnvSettings:
    load_dotenv(".env")

    return EnvSettings(
        github_token=os.getenv("GITHUB_ACCESS_TOKEN", ""),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        dockerhub_user=os.getenv("DOCKERHUB_USER", ""),
        dockerhub_repo=os.getenv("DOCKERHUB_REPO", ""),
    )