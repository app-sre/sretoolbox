import re

import pytest

from sretoolbox.utils.k8s import unique_job_name


@pytest.mark.parametrize(
    "name,suffix,expected_pattern",
    [
        # Basic usage with defaults
        ("myjob", "", r"^myjob-[a-f0-9]{8}$"),
        # With custom suffix
        ("myjob", "custom", r"^myjob-custom$"),
        # Suffix already has dash
        ("myjob", "-custom", r"^myjob-custom$"),
        # Both have already dashes
        ("myjob-", "-custom", r"^myjob-custom$"),
    ],
)
def test_unique_job_name_patterns(
    name: str, suffix: str, expected_pattern: str
) -> None:
    result = unique_job_name(name, suffix)
    assert re.match(expected_pattern, result), (
        f"Result '{result}' does not match pattern '{expected_pattern}'"
    )


@pytest.mark.parametrize(
    "name,suffix,max_length,expected_length",
    [
        # Within limit
        ("myjob", "1", 63, 7),
        # At exact limit
        ("a" * 61, "1", 63, 63),
        # Exceeds limit - should truncate name
        ("verylongjobname" * 10, "1", 63, 63),
        # Very short max_length
        ("myjob", "1", 5, 5),
        # Default max_length with long name
        ("a" * 100, "", 63, 63),
    ],
)
def test_unique_job_name_length(
    name: str, suffix: str, max_length: int, expected_length: int
) -> None:
    result = unique_job_name(name, suffix, max_length)
    assert len(result) == expected_length, (
        f"Result '{result}' length {len(result)} does not match expected {expected_length}"
    )


def test_unique_job_name_uniqueness() -> None:
    """Test that multiple calls generate unique names when using default suffix."""
    name = "myjob"
    results = [unique_job_name(name) for _ in range(10)]
    assert len(results) == len(set(results)), "Generated names are not unique"


def test_unique_job_name_truncation() -> None:
    """Test that name truncation preserves prefix and suffix."""
    assert (
        unique_job_name("verylongjobname" * 10, "mysuffix", 30)
        == "verylongjobnameverylo-mysuffix"
    )


@pytest.mark.parametrize(
    ("name", "suffix"),
    [
        ("validname", "suffix"),
        ("valid-name-123", "suffix"),
        ("a" * 63, "suffix"),
        ("name-with-multiple-dashes-123", "suffix"),
        # edge cases
        ("InvalidName", "suffix"),
        ("name_with_underscores", "suffix"),
        ("name.with.dots", "suffix"),
        ("-startswithdash", "suffix"),
        ("endswithdash", "suffix-"),
        ("name with spaces", "suffix"),
    ],
)
def test_unique_job_name_valid_k8s_name(name: str, suffix: str) -> None:
    """Test that generated names are valid Kubernetes resource names."""
    result = unique_job_name(name, suffix)

    # K8s names must be lowercase alphanumeric or '-'
    # Must not start or end with dash
    assert re.match(r"^[a-z0-9-]+$", result), f"Invalid K8s name: {result}"
    assert len(result) <= 63, "K8s names must be <= 63 characters"
    assert len(result) > 0, "K8s names must be non-empty"
