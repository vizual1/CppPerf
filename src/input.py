import argparse, sys
from src.core.controller import Controller
from src.config.config import *

def add_output_args(p):
    group = p.add_argument_group("Output")
    group.add_argument("--output", type=str, default="")

def add_input_args(p):
    group = p.add_argument_group("Input")
    group.add_argument("--input", type=str, default="")

def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GitHub automation tool: collect repos, gather commits, and run tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    discover = subparsers.add_parser("discover", help="Mining, filtering and validation of repositories or commits.")
    discover.add_argument("--test", action="store_true", help="Validate the build and test (most recent commit) of the mined repositories, or Build, tests, evaluate and containerize collected and filtered commits.")
    add_input_args(discover)
    add_output_args(discover)
    validate = subparsers.add_parser("validate", help="Addition to discover command for validation of repositories or commits if not done before.")
    add_input_args(validate)
    add_output_args(validate)
    benchmark = subparsers.add_parser("benchmark", help="Benchmarking docker images and docker images with patches.")
    add_input_args(benchmark)
    add_output_args(benchmark)
    artifact = subparsers.add_parser("artifact")
    add_input_args(artifact)
    add_output_args(artifact)

    source_group = discover.add_argument_group("Source Options")
    source_group.add_argument("--repos", type=int, default=10, help="Limit number of mined repositories (default: 10)")
    source_group.add_argument("--stars", type=int, default=1000, help="Maximum popularity (star count) for mined repositories (default: 1000).")
    source_group.add_argument("--min_stars", type=int, default=20, help="Minimum popularity (star count) for mined repositories (default: 20).")
    source_group.add_argument("--blacklist", type=str, help="Blacklist to skip repositories in the mining process.")

    filter_group = discover.add_argument_group("Filtering")
    filter_group.add_argument("--filter", choices=["simple", "llm", "issue"])
    filter_group.add_argument("--limit", type=int, default=-1, help="Limits amount of commits collected from repositories (default -1 = all commits).")

    test_group = validate.add_argument_group("Testing")
    test_group.add_argument("--repositories", action="store_true", help="--test without mining for repositories. requires input file.")
    test_group.add_argument("--commits", action="store_true", help="--test without filtering for commits, requires input file.")

    docker_group = benchmark.add_argument_group("Docker Benchmark")
    docker_group.add_argument("--docker", type=str, help="Test and evaluate docker images of commits.")
    docker_group.add_argument("--diff", type=str, help="Applies the diff patch to the old (original) commit in the docker container.")

    artifact_group = artifact.add_argument_group("Artifacts")
    artifact_group.add_argument("--generate", action="store_true", help="Given a folder of json files of commits evaluations generated with discover or validate, create a docker image for each json file (no test run).")
    artifact_group.add_argument("--pull", action="store_true", help="Given a folder of json files of commits evaluations generated with discover or validate, pull the docker image from Dockerhub if it exists.")
    artifact_group.add_argument("--push", action="store_true", help="Given a folder of json files of commits evaluations generated with discover or validate, push the image to Dockerhub (Docker image must exist before, else run --generate first).")
    
    return parser


def create_config(args: argparse.Namespace) -> Config:
    """Create a Config object from argparse arguments."""
    try:
        cfg = Config(
            command=args.command,
            input=args.input,
            output=args.output
        )

        if args.command == "discover":
            cfg.discover = DiscoverConfig(
                repos=args.repos,
                stars=args.stars,
                min_stars=args.min_stars,
                filter=args.filter,
                test=args.test,
                limit=args.limit,
                blacklist=args.blacklist
            )

        elif args.command == "validate":
            cfg.validate = ValidateConfig(
                repositories=args.repositories,
                commits=args.commits,
            )

        elif args.command == "benchmark":
            cfg.benchmark = BenchmarkConfig(
                docker=args.docker,
                diff=args.diff,
            )

        elif args.command == "artifact":
            cfg.artifact = ArtifactConfig(
                generate=args.generate,
                pull=args.pull,
                push=args.push,
            )

        return cfg
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(2)


def start() -> None:
    parser = setup_parser()
    args = parser.parse_args()
    config = create_config(args)
    pipeline = Controller(config=config)
    pipeline.run()


if __name__ == "__main__":
    start()
