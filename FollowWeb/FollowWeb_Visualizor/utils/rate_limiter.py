"""
Rate limiting utilities for API requests.

This module provides thread-safe rate limiting using the token bucket algorithm
to prevent exceeding API rate limits and ensure smooth request distribution.
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
    
    Attributes:
        requests_per_minute: Maximum number of requests allowed per minute
        tokens: Current number of available tokens
        last_update: Timestamp of last token refill
        lock: Thread lock for thread-safe operations
        logger: Logger instance for rate limit events
    
    Example:
        >>> limiter = RateLimiter(requests_per_minute=60)
        >>> limiter.acquire()  # Blocks until token is available
        >>> # Make API request here
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter with specified rate.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute (default: 60)
        
        Raises:
            ValueError: If requests_per_minute is not positive
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
