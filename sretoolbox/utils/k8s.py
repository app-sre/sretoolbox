import re
import uuid


def unique_job_name(name: str, suffix: str = "", max_length: int = 63) -> str:
    """Generate a unique Kubernetes job name with an optional given prefix.

    Args:
        name (str): Base name for the job.
        suffix (str, optional): Unique suffix to add to the job name. Defaults to a "-" followed by a random UUID if not provided.
        max_length (int, optional): Maximum length of the job name. Defaults to 63

    Returns:
        str: A unique job name.
    """
    if len(suffix) >= max_length:
        raise ValueError("Suffix length must be less than max_length")
    if not suffix:
        suffix = uuid.uuid4().hex[:8]
    if not suffix.startswith("-"):
        suffix = "-" + suffix

    # shorten the name if necessary to fit within max_length
    name = name[: max_length - len(suffix)]

    # convert to valid k8s name
    full_name = f"{name}{suffix}"
    full_name = re.sub(r"[^a-z0-9-]", "-", full_name.lower())
    full_name = re.sub(r"-+", "-", full_name)
    return full_name.strip("-")
