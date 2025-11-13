"""
Rate limiting utilities for API requests.

This module provides thread-safe rate limiting using the token bucket algorithm
to prevent exceeding API rate limits and ensure smooth request distribution.

The token bucket algorithm allows bursts of requests up to the bucket capacity
while maintaining an average rate over time. This is ideal for API rate limiting
where occasional bursts are acceptable but sustained high rates must be prevented.

Classes:
    RateLimiter: Thread-safe rate limiter using token bucket algorithm

Example:
    Basic usage::

        from FollowWeb_Visualizor.utils.rate_limiter import RateLimiter

        # Create limiter for 60 requests per minute
        limiter = RateLimiter(requests_per_minute=60)

        # Make API requests
        for i in range(100):
            limiter.acquire()  # Blocks until token is available
            response = make_api_request()
            print(f"Request {i}: {response.status_code}")

    With timeout::

        limiter = RateLimiter(requests_per_minute=60)

        if limiter.acquire(timeout=5.0):
            # Token acquired within 5 seconds
            response = make_api_request()
        else:
            # Timeout - handle gracefully
            print("Rate limit timeout")

    Multi-threaded usage::

        import threading

        limiter = RateLimiter(requests_per_minute=60)

        def worker():
            for i in range(10):
                limiter.acquire()
                make_api_request()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

See Also:
    :class:`~FollowWeb_Visualizor.data.loaders.freesound.FreesoundLoader`: Uses RateLimiter

Notes:
    The token bucket algorithm works as follows:

    1. Bucket starts full with N tokens (N = requests_per_minute)
    2. Tokens are consumed when requests are made
    3. Tokens are refilled continuously at the configured rate
    4. If bucket is empty, requests block until tokens are available

    This allows bursts up to N requests, then throttles to the average rate.
"""

import logging
import threading
import time
from typing import Optional


class RateLimiter:
    """
    Thread-safe rate limiter using token bucket algorithm.

    The token bucket algorithm allows bursts of requests up to the bucket capacity
    while maintaining an average rate over time. Tokens are refilled continuously
    based on the configured rate.

    This implementation is thread-safe and can be shared across multiple threads
    making concurrent API requests. The limiter ensures that the total request
    rate across all threads does not exceed the configured limit.

    Attributes
    ----------
    rate : int
        Maximum number of requests allowed per minute
    tokens : float
        Current number of available tokens (may be fractional)
    last_update : float
        Timestamp of last token refill (seconds since epoch)
    lock : threading.Lock
        Thread lock for thread-safe operations
    logger : logging.Logger
        Logger instance for rate limit events

    Notes
    -----
    The token bucket algorithm:

    - Starts with a full bucket (rate tokens)
    - Consumes tokens when requests are made
    - Refills tokens continuously at (rate / 60) tokens per second
    - Blocks requests when bucket is empty
    - Allows bursts up to the bucket capacity

    This is more adaptable than a simple fixed-rate limiter because it allows
    occasional bursts while still maintaining the average rate over time.

    The refill rate is calculated as: rate / 60 tokens per second
    For example, 60 requests/minute = 1 token per second

    Examples
    --------
    Basic usage::

        limiter = RateLimiter(requests_per_minute=60)
        limiter.acquire()  # Blocks until token is available
        make_api_request()

    With multiple tokens::

        limiter = RateLimiter(requests_per_minute=60)
        limiter.acquire(tokens=5)  # Acquire 5 tokens at once
        make_batch_request(size=5)

    Check available tokens::

        limiter = RateLimiter(requests_per_minute=60)
        available = limiter.get_available_tokens()
        print(f"Can make {int(available)} requests immediately")

    Calculate wait time::

        limiter = RateLimiter(requests_per_minute=60)
        wait_time = limiter.wait_for_capacity(tokens=10)
        print(f"Need to wait {wait_time:.2f} seconds for 10 tokens")

    See Also
    --------
    acquire : Acquire tokens from the bucket
    get_available_tokens : Get current token count
    wait_for_capacity : Calculate wait time for tokens
    reset : Reset bucket to full capacity
    """

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter with specified rate.

        Parameters
        ----------
        requests_per_minute : int, optional
            Maximum requests allowed per minute (default: 60).
            This is both the bucket capacity and the refill rate.

        Raises
        ------
        ValueError
            If requests_per_minute is not positive (must be >= 1).

        Notes
        -----
        The bucket starts full with requests_per_minute tokens, allowing
        an initial burst of requests up to the limit.

        The refill rate is: requests_per_minute / 60 tokens per second

        Examples
        --------
        Standard rate (60 requests/minute)::

            limiter = RateLimiter()  # Uses default 60

        Conservative rate (30 requests/minute)::

            limiter = RateLimiter(requests_per_minute=30)

        High rate (120 requests/minute)::

            limiter = RateLimiter(requests_per_minute=120)
        """
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")

        self.rate = requests_per_minute
        self.tokens = float(requests_per_minute)
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        self.logger.info(
            f"RateLimiter initialized: {requests_per_minute} requests/minute"
        )

    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire tokens from the bucket, blocking until available.

        This method blocks the calling thread until the requested number of tokens
        becomes available. Tokens are refilled continuously based on the configured
        rate.

        Args:
            tokens: Number of tokens to acquire (default: 1)
            timeout: Maximum time to wait in seconds (None = wait indefinitely)

        Returns:
            True if tokens were acquired, False if timeout was reached

        Raises:
            ValueError: If tokens is not positive

        Example:
            >>> limiter = RateLimiter(requests_per_minute=60)
            >>> if limiter.acquire(tokens=1, timeout=5.0):
            ...     # Make API request
            ...     pass
            ... else:
            ...     # Handle timeout
            ...     pass
        """
        if tokens <= 0:
            raise ValueError("tokens must be positive")

        start_time = time.time()
        wait_logged = False

        with self.lock:
            while True:
                self._refill_tokens()

                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    if wait_logged:
                        elapsed = time.time() - start_time
                        self.logger.info(
                            f"Rate limit wait completed after {elapsed:.2f}s"
                        )
                    return True

                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        self.logger.warning(
                            f"Rate limit timeout after {elapsed:.2f}s "
                            f"(needed {tokens} tokens, have {self.tokens:.2f})"
                        )
                        return False

                # Log waiting message (only once per acquire call)
                if not wait_logged:
                    wait_time = (tokens - self.tokens) / (self.rate / 60.0)
                    self.logger.debug(
                        f"Rate limit reached, waiting ~{wait_time:.2f}s "
                        f"(need {tokens} tokens, have {self.tokens:.2f})"
                    )
                    wait_logged = True

                # Release lock briefly to allow other threads
                self.lock.release()
                time.sleep(0.1)
                self.lock.acquire()

    def _refill_tokens(self) -> None:
        """
        Refill tokens based on elapsed time since last update.

        This method is called internally by acquire() and should not be called
        directly. It calculates how many tokens should be added based on the
        time elapsed since the last refill.

        The refill rate is: (requests_per_minute / 60) tokens per second
        """
        now = time.time()
        elapsed = now - self.last_update

        # Calculate new tokens based on elapsed time
        # Rate is requests per minute, so divide by 60 for per-second rate
        new_tokens = elapsed * (self.rate / 60.0)

        # Add new tokens but don't exceed bucket capacity
        self.tokens = min(self.rate, self.tokens + new_tokens)
        self.last_update = now

    def get_available_tokens(self) -> float:
        """
        Get current number of available tokens.

        This method is thread-safe and updates the token count before returning.

        Returns:
            Current number of available tokens (may be fractional)

        Example:
            >>> limiter = RateLimiter(requests_per_minute=60)
            >>> available = limiter.get_available_tokens()
            >>> print(f"Available tokens: {available:.2f}")
        """
        with self.lock:
            self._refill_tokens()
            return self.tokens

    def reset(self) -> None:
        """
        Reset the rate limiter to full capacity.

        This method refills the bucket to maximum capacity and resets the
        last update timestamp. Useful for testing or manual rate limit resets.

        Example:
            >>> limiter = RateLimiter(requests_per_minute=60)
            >>> limiter.acquire(tokens=50)
            >>> limiter.reset()  # Refill to 60 tokens
        """
        with self.lock:
            self.tokens = float(self.rate)
            self.last_update = time.time()
            self.logger.info("RateLimiter reset to full capacity")

    def wait_for_capacity(self, required_tokens: int = 1) -> float:
        """
        Calculate wait time needed for required tokens to become available.

        This method does not block or consume tokens. It only calculates how
        long the caller would need to wait for the specified number of tokens.

        Args:
            required_tokens: Number of tokens needed

        Returns:
            Wait time in seconds (0 if tokens are already available)

        Example:
            >>> limiter = RateLimiter(requests_per_minute=60)
            >>> wait_time = limiter.wait_for_capacity(tokens=10)
            >>> print(f"Need to wait {wait_time:.2f} seconds")
        """
        with self.lock:
            self._refill_tokens()

            if self.tokens >= required_tokens:
                return 0.0

            # Calculate how long until we have enough tokens
            tokens_needed = required_tokens - self.tokens
            wait_time = tokens_needed / (self.rate / 60.0)

            return wait_time
