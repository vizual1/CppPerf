import os, requests, docker, logging

def image(repo_id: str, sha: str) -> str:
    return ("_".join(repo_id.split("/")) + f"_{sha}").lower()

def image_exists(repo_id: str = "", sha: str = "", other: str = "") -> bool:
    image_name = other if other else image(repo_id, sha)
    client = docker.from_env()
    try:
        client.images.get(image_name)
        return True
    except docker.errors.ImageNotFound: #type:ignore
        return False
    except docker.errors.APIError: #type:ignore
        return False
    
def delete_image(repo_id: str = "", sha: str = "", other: str = "") -> None:
    image_name = other if other else image(repo_id, sha)
    client = docker.from_env()
    try:
        client.images.remove(image=image_name, force=True)
        logging.info(f"Image '{image_name}' has been deleted.")
    except docker.errors.ImageNotFound: #type:ignore
        logging.info(f"Image '{image_name}' not found.")
    except docker.errors.APIError as e: #type:ignore
        logging.info(f"Failed to delete image: {e}")

def dockerhub_containers(dockerhub_user: str, dockerhub_repo: str) -> list[str]:
    tags = []
    url = f"https://hub.docker.com/v2/repositories/{dockerhub_user}/{dockerhub_repo}/tags?page_size=100"

    while url:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()

        for r in data["results"]:
            tags.append(r["name"])

        url = data["next"]  # None when no more pages

    return tags
