"""Runtime configuration management."""
import yaml
from dataclasses import dataclass, field
from typing import Optional
from github import Auth, Github

from src.config.prompts import Prompts
from src.config.constants import *
from src.config.settings import LLMSettings, TestingSettings, ResourceSettings
from src.config.env_loader import EnvSettings
from src.utils.image_handling import dockerhub_containers
from src.config.env_loader import load_env

@dataclass
class DiscoverConfig:
    repos: int = 0
    stars: int = 1000000
    min_stars: int = 20
    filter: str = ""
    test: bool = False
    limit: int = -1
    blacklist: str = ""

@dataclass
class ValidateConfig:
    repositories: bool = False
    commits: bool = False

@dataclass
class BenchmarkConfig:
    docker: str = ""
    diff: str = ""

@dataclass
class ArtifactConfig:
    generate: bool = True
    pull: bool = False
    push: bool = False

@dataclass
class InspectConfig:
    repo: str = ""
    sha: str = ""
    id: str = ""

@dataclass
class Config:
    """
    GitHub Repository Collection, Structural, Build and Test Validation
    """
    command: str = ""
    input: str = ""
    output: str = ""
    env: Optional[EnvSettings] = field(init=False, default=None)

    discover: DiscoverConfig = field(default_factory=DiscoverConfig)
    validate: ValidateConfig = field(default_factory=ValidateConfig)
    benchmark: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    artifact: ArtifactConfig = field(default_factory=ArtifactConfig)
    inspect: InspectConfig = field(default_factory=InspectConfig)
    
    """
    Configurations Settings
    """
    llm: LLMSettings = field(default_factory=LLMSettings)
    testing: TestingSettings = field(default_factory=TestingSettings)
    resources: ResourceSettings = field(default_factory=ResourceSettings)
    prompts: Prompts = field(default_factory=Prompts)

    """
    Constants
    """
    storage_paths: dict = field(default_factory=lambda: STORAGE_PATHS)
    valid_test_dirs: set = field(default_factory=lambda: VALID_TEST_DIRS)
    test_keywords: list = field(default_factory=lambda: TEST_KEYWORDS)
    docker_map: dict = field(default_factory=lambda: DOCKER_IMAGE_MAP)
    commits_time: dict = field(default_factory=lambda: COMMIT_TIME)
    valid_test_flags: dict = field(default_factory=lambda: VALID_TEST_FLAGS)
    
    """
    GitHub
    """
    _auth: Optional[Auth.Token] = field(init=False, default=None)
    _git: Optional[Github] = field(init=False, default=None)

    def __post_init__(self):
        self.env = load_env()

        load_runtime_overrides(
            self.llm,
            self.testing,
            self.resources
        )

        if self.llm.ollama_enabled:
            self.llm.ollama_stage1_model = self.llm.model1
            self.llm.ollama_stage2_model = self.llm.model2
            self.llm.ollama_resolver_model = self.llm.resolver_model
            self.llm.ollama_url = self.llm.base_url

        self._validate()
        self._setup_github()
        if self.env and self.command == "artifact" and (self.artifact.pull or self.artifact.push):
            self.dockerhub_containers = dockerhub_containers(self.env.dockerhub_user, self.env.dockerhub_repo)
        
    def _validate(self) -> None:
        """Validate configuration consistency."""
        if not self.env:
            raise ValueError(f"Environment error: environment not set")

        if self.discover.filter not in ("simple", "llm", "issue", ""):
            raise ValueError(f"Unknown filter type: {self.discover.filter}")

        if str(self.testing.docker_test_dir) == "/workspace":
            raise ValueError("Docker test directory cannot be '/workspace'")

    def _setup_github(self):
        """Initialize GitHub client."""
        self._auth = Auth.Token(self.env.github_token if self.env else "")
        self._git = Github(auth=self._auth)

    @property
    def git_client(self) -> Github:
        """Get the GitHub client (read-only)."""
        if self._git is None:
            raise RuntimeError("GitHub client not initialized")
        return self._git
    

def apply_overrides(obj, values: dict):
    for key, value in values.items():
        if hasattr(obj, key):
            setattr(obj, key, value)

def load_runtime_overrides(
    llm,
    testing,
    resources,
    path: str = "config/config.yaml"
):
    config_path = Path(path)

    if not config_path.exists():
        return

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    apply_overrides(llm, raw.get("llm", {}))
    apply_overrides(testing, raw.get("testing", {}))
    apply_overrides(resources, raw.get("resources", {}))

    benchmark = raw.get("benchmark", {})
    apply_overrides(testing, benchmark)