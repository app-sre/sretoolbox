import re

import pytest

from sretoolbox.utils.k8s import unique_job_name


@pytest.mark.parametrize(
    "name,prefix,suffix,max_length,expected_pattern",
    [
        # Basic usage with defaults
        ("myjob", "", "", 63, r"^myjob-[a-f0-9]{8}$"),
        # With custom prefix
        ("myjob", "test", "", 63, r"^test-myjob-[a-f0-9]{8}$"),
        # With custom suffix
        ("myjob", "", "custom", 63, r"^myjob-custom$"),
        # With both prefix and suffix
        ("myjob", "test", "custom", 63, r"^test-myjob-custom$"),
        # Prefix already has dash
        ("myjob", "test-", "", 63, r"^test-myjob-[a-f0-9]{8}$"),
        # Suffix already has dash
        ("myjob", "", "-custom", 63, r"^myjob-custom$"),
        # Both prefix and suffix with dashes
        ("myjob", "prefix-", "-suffix", 63, r"^prefix-myjob-suffix$"),
    ],
)
def test_unique_job_name_patterns(
    name: str, prefix: str, suffix: str, max_length: int, expected_pattern: str
) -> None:
    result = unique_job_name(name, prefix, suffix, max_length)
    assert re.match(expected_pattern, result), (
        f"Result '{result}' does not match pattern '{expected_pattern}'"
    )


@pytest.mark.parametrize(
    "name,prefix,suffix,max_length,expected_length",
    [
        # Within limit
        ("myjob", "1", "1", 63, 9),
        # At exact limit
        ("a" * 59, "1", "1", 63, 63),
        # Exceeds limit - should truncate name
        ("verylongjobname" * 10, "1", "1", 63, 63),
        # Very short max_length
        ("myjob", "1", "1", 8, 8),
        # Default max_length with long name
        ("a" * 100, "", "", 63, 63),
    ],
)
def test_unique_job_name_length(
    name: str, prefix: str, suffix: str, max_length: int, expected_length: int
) -> None:
    result = unique_job_name(name, prefix, suffix, max_length)
    assert len(result) <= max_length, (
        f"Result '{result}' exceeds max_length {max_length}"
    )
    if prefix and suffix:
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
        unique_job_name("verylongjobname" * 10, "myprefix", "mysuffix", 30)
        == "myprefix-verylongjobn-mysuffix"
    )


@pytest.mark.parametrize(
    ("name", "prefix", "suffix"),
    [
        ("validname", "prefix", "suffix"),
        ("valid-name-123", "prefix", "suffix"),
        ("a" * 63, "prefix", "suffix"),
        ("name-with-multiple-dashes-123", "prefix", "suffix"),
        # edge cases
        ("InvalidName", "prefix", "suffix"),
        ("name_with_underscores", "prefix", "suffix"),
        ("name.with.dots", "prefix", "suffix"),
        ("startswithdash", "-prefix", "suffix"),
        ("endswithdash", "prefix", "suffix-"),
        ("name with spaces", "prefix", "suffix"),
    ],
)
def test_unique_job_name_valid_k8s_name(name: str, prefix: str, suffix: str) -> None:
    """Test that generated names are valid Kubernetes resource names."""
    result = unique_job_name(name, prefix, suffix)

    # K8s names must be lowercase alphanumeric or '-'
    # Must not start or end with dash
    assert re.match(r"^[a-z0-9-]+$", result), f"Invalid K8s name: {result}"
    assert len(result) <= 63, "K8s names must be <= 63 characters"
    assert len(result) > 0, "K8s names must be non-empty"
