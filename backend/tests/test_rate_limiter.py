import time
from unittest.mock import patch
from app.utils.rate_limiter import RateLimiter


def test_allow_under_limit():
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert limiter.allow("user1") is True


def test_block_over_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.allow("user1")
    assert limiter.allow("user1") is False


def test_separate_keys():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    limiter.allow("user1")
    limiter.allow("user1")
    assert limiter.allow("user1") is False
    assert limiter.allow("user2") is True  # Different key


def test_remaining():
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    assert limiter.remaining("user1") == 5
    limiter.allow("user1")
    limiter.allow("user1")
    assert limiter.remaining("user1") == 3


def test_window_expiry():
    limiter = RateLimiter(max_requests=2, window_seconds=1)
    limiter.allow("user1")
    limiter.allow("user1")
    assert limiter.allow("user1") is False

    # Simulate time passing beyond window
    with patch("app.utils.rate_limiter.time") as mock_time:
        mock_time.time.return_value = time.time() + 2
        assert limiter.allow("user1") is True


def test_remaining_after_expiry():
    limiter = RateLimiter(max_requests=3, window_seconds=1)
    limiter.allow("user1")
    limiter.allow("user1")

    with patch("app.utils.rate_limiter.time") as mock_time:
        mock_time.time.return_value = time.time() + 2
        assert limiter.remaining("user1") == 3
