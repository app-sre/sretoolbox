import re
import uuid


def unique_job_name(
    name: str, prefix: str = "", suffix: str = "", max_length: int = 63
) -> str:
    """Generate a unique Kubernetes job name with an optional given prefix.

    Args:
        name (str): Base name for the job.
        prefix (str, optional): Prefix to add to the job name. Defaults to "".
        suffix (str, optional): Suffix to add to the job name. Defaults to a random UUID.

    Returns:
        str: A unique job name.
    """
    if prefix and not prefix.endswith("-"):
        prefix += "-"
    if not suffix:
        suffix = uuid.uuid4().hex[:8]
    if not suffix.startswith("-"):
        suffix = "-" + suffix

    # shorten the name if necessary to fit within max_length
    total_length = len(prefix) + len(name) + len(suffix)
    if total_length > max_length:
        excess_length = total_length - max_length
        name = name[:-excess_length]

    # convert to valid k8s name
    full_name = f"{prefix}{name}{suffix}"
    full_name = re.sub(r"[^a-z0-9-]", "-", full_name.lower())
    full_name = re.sub(r"-+", "-", full_name)
    return full_name.strip("-")
