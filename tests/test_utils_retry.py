# Copyright 2021 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

from unittest.mock import patch

import pytest

from sretoolbox.utils.retry import retry


class TestRetryDecorator:
    def test_success_without_retry(self) -> None:
        calls = 0

        @retry()
        def succeeds() -> str:
            nonlocal calls
            calls += 1
            return "ok"

        with patch("sretoolbox.utils.retry.time.sleep") as sleep:
            assert succeeds() == "ok"

        assert calls == 1
        sleep.assert_not_called()

    def test_linear_backoff_matches_legacy_behavior(self) -> None:
        calls = 0

        @retry(max_attempts=3, exceptions=ValueError)
        def flaky() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ValueError("fail")
            return "ok"

        with patch("sretoolbox.utils.retry.time.sleep") as sleep:
            assert flaky() == "ok"

        assert calls == 3
        sleep.assert_any_call(1)
        sleep.assert_any_call(2)
        assert sleep.call_count == 2

    def test_exponential_backoff(self) -> None:
        calls = 0

        @retry(
            max_attempts=4,
            exceptions=RuntimeError,
            backoff="exponential",
            backoff_base=2.0,
        )
        def flaky() -> None:
            nonlocal calls
            calls += 1
            raise RuntimeError("fail")

        with (
            patch("sretoolbox.utils.retry.time.sleep") as sleep,
            pytest.raises(RuntimeError),
        ):
            flaky()

        assert calls == 4
        sleep.assert_any_call(1.0)
        sleep.assert_any_call(2.0)
        sleep.assert_any_call(4.0)
        assert sleep.call_count == 3

    def test_exponential_backoff_with_max(self) -> None:
        calls = 0

        @retry(
            max_attempts=5,
            exceptions=RuntimeError,
            backoff="exponential",
            backoff_base=2.0,
            backoff_max=3.0,
        )
        def flaky() -> None:
            nonlocal calls
            calls += 1
            raise RuntimeError("fail")

        with (
            patch("sretoolbox.utils.retry.time.sleep") as sleep,
            pytest.raises(RuntimeError),
        ):
            flaky()

        sleep.assert_any_call(1.0)
        sleep.assert_any_call(2.0)
        sleep.assert_any_call(3.0)
        assert sleep.call_count == 4

    def test_jitter_passes_randomized_delay_to_sleep(self) -> None:
        calls = 0

        @retry(
            max_attempts=2,
            exceptions=ValueError,
            backoff="exponential",
            backoff_base=2.0,
            jitter=True,
        )
        def flaky() -> None:
            nonlocal calls
            calls += 1
            raise ValueError("fail")

        with (
            patch("sretoolbox.utils.retry.random.uniform", return_value=0.25),
            patch("sretoolbox.utils.retry.time.sleep") as sleep,
            pytest.raises(ValueError),
        ):
            flaky()

        sleep.assert_called_once_with(0.25)

    def test_no_retry_exceptions(self) -> None:
        @retry(exceptions=Exception, no_retry_exceptions=(TypeError,))
        def raises_type_error() -> None:
            raise TypeError("no retry")

        with (
            patch("sretoolbox.utils.retry.time.sleep") as sleep,
            pytest.raises(TypeError),
        ):
            raises_type_error()

        sleep.assert_not_called()

    def test_hook_legacy_signature(self) -> None:
        calls = 0
        hook_calls: list[Exception] = []

        def hook(exc: Exception) -> None:
            hook_calls.append(exc)

        @retry(max_attempts=2, exceptions=ValueError, hook=hook)
        def flaky() -> None:
            nonlocal calls
            calls += 1
            raise ValueError("fail")

        with (
            patch("sretoolbox.utils.retry.time.sleep"),
            pytest.raises(ValueError),
        ):
            flaky()

        assert len(hook_calls) == 1
        assert isinstance(hook_calls[0], ValueError)

    def test_hook_with_attempt_context(self) -> None:
        hook_calls: list[tuple[Exception, int, int]] = []

        def hook(exc: Exception, attempt: int, max_attempts: int) -> None:
            hook_calls.append((exc, attempt, max_attempts))

        calls = 0

        @retry(max_attempts=3, exceptions=OSError, hook=hook)
        def flaky() -> None:
            nonlocal calls
            calls += 1
            raise OSError("fail")

        with (
            patch("sretoolbox.utils.retry.time.sleep"),
            pytest.raises(OSError),
        ):
            flaky()

        assert hook_calls == [
            (hook_calls[0][0], 1, 3),
            (hook_calls[1][0], 2, 3),
        ]
        assert all(isinstance(exc, OSError) for exc, _, _ in hook_calls)

    def test_invalid_max_attempts(self) -> None:
        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            retry(max_attempts=0)

    def test_invalid_exponential_backoff_base(self) -> None:
        with pytest.raises(ValueError, match="backoff_base must be > 0"):
            retry(backoff="exponential", backoff_base=0)
