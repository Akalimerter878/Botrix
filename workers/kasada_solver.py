"""Kasada challenge solver for Kick.com"""

import asyncio
import aiohttp
import time
from typing import Optional, Dict, Literal
from datetime import datetime
from .utils import get_logger

logger = get_logger(__name__)


class KasadaSolverError(Exception):
    """Base exception for KasadaSolver errors"""
    pass


class InvalidAPIKeyError(KasadaSolverError):
    """Raised when API key is invalid"""
    pass


class RateLimitError(KasadaSolverError):
    """Raised when rate limit is exceeded"""
    pass


class TimeoutError(KasadaSolverError):
    """Raised when request times out"""
    pass


class KasadaSolver:
    """
    Handles Kasada protection bypass using RapidAPI
    
    Features:
    - Retry logic with exponential backoff
    - Rate limiting (1 req/sec for free tier)
    - Timeout handling (30 seconds max)
    - Test mode for development
    - Detailed logging
    """

    RAPIDAPI_HOST = "kasada-reverse.p.rapidapi.com"
    RAPIDAPI_URL = f"https://{RAPIDAPI_HOST}/kasada"
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30
    RATE_LIMIT_DELAY = 1.0  # 1 second between requests for free tier

    def __init__(self, api_key: str, test_mode: bool = False):
        """
        Initialize KasadaSolver
        
        Args:
            api_key: RapidAPI key for Kasada solver
            test_mode: If True, return mock data without calling API
        """
        if not api_key and not test_mode:
            raise InvalidAPIKeyError("API key is required when not in test mode")
        
        self.api_key = api_key
        self.test_mode = test_mode
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time: float = 0
        
        logger.info(f"KasadaSolver initialized (test_mode={test_mode})")

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp session")

    async def _enforce_rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.RATE_LIMIT_DELAY:
            wait_time = self.RATE_LIMIT_DELAY - time_since_last_request
            logger.debug(f"Rate limit: waiting {wait_time:.2f}s before next request")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

    def _get_mock_response(self, method: str, fetch_url: str) -> Dict:
        """
        Generate mock response for test mode
        
        Args:
            method: HTTP method
            fetch_url: Target URL
            
        Returns:
            Mock Kasada headers
        """
        logger.info(f"[TEST MODE] Returning mock Kasada headers for {fetch_url}")
        return {
            "x-kpsdk-cd": "mock-cd-token-12345",
            "x-kpsdk-ct": "mock-ct-token-67890",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "cookie": "mock-kasada-cookie=test123"
        }

    async def solve(
        self, 
        method: Literal["GET", "POST", "PUT", "DELETE"] = "POST",
        fetch_url: str = ""
    ) -> Dict:
        """
        Solve Kasada challenge and return headers
        
        Args:
            method: HTTP method for the request (default: POST)
            fetch_url: Target URL that needs Kasada bypass
            
        Returns:
            Dictionary containing Kasada headers to use in requests
            
        Raises:
            InvalidAPIKeyError: If API key is invalid
            RateLimitError: If rate limit is exceeded
            TimeoutError: If request times out
            KasadaSolverError: For other API errors
        """
        logger.info(f"Solving Kasada challenge - Method: {method}, URL: {fetch_url}")
        
        # Return mock data in test mode
        if self.test_mode:
            await asyncio.sleep(0.1)  # Simulate API delay
            return self._get_mock_response(method, fetch_url)
        
        # Validate inputs
        if not fetch_url:
            raise ValueError("fetch_url is required")
        
        # Try with retries
        last_exception = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(f"Attempt {attempt}/{self.MAX_RETRIES}")
                
                # Enforce rate limiting
                await self._enforce_rate_limit()
                
                # Make API request
                result = await self._make_api_request(method, fetch_url)
                
                logger.info(f"Successfully solved Kasada challenge on attempt {attempt}")
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = TimeoutError(f"Request timed out after {self.TIMEOUT_SECONDS}s")
                logger.warning(f"Attempt {attempt} timed out: {e}")
                
            except InvalidAPIKeyError as e:
                # Don't retry on invalid API key
                logger.error(f"Invalid API key: {e}")
                raise
                
            except RateLimitError as e:
                # Don't retry on rate limit (user should wait)
                logger.error(f"Rate limit exceeded: {e}")
                raise
                
            except aiohttp.ClientError as e:
                last_exception = KasadaSolverError(f"API connection failed: {e}")
                logger.warning(f"Attempt {attempt} failed with client error: {e}")
                
            except Exception as e:
                last_exception = KasadaSolverError(f"Unexpected error: {e}")
                logger.error(f"Attempt {attempt} failed with unexpected error: {e}")
            
            # Exponential backoff before retry
            if attempt < self.MAX_RETRIES:
                backoff_time = 2 ** attempt  # 2, 4, 8 seconds
                logger.debug(f"Waiting {backoff_time}s before retry...")
                await asyncio.sleep(backoff_time)
        
        # All attempts failed
        error_msg = f"Failed to solve Kasada challenge after {self.MAX_RETRIES} attempts"
        logger.error(error_msg)
        raise last_exception if last_exception else KasadaSolverError(error_msg)

    async def _make_api_request(self, method: str, fetch_url: str) -> Dict:
        """
        Make the actual API request to RapidAPI
        
        Args:
            method: HTTP method
            fetch_url: Target URL
            
        Returns:
            Kasada headers from API response
        """
        await self._ensure_session()
        
        # Prepare request
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.RAPIDAPI_HOST,
            "Content-Type": "application/json"
        }
        
        payload = {
            "method": method,
            "url": fetch_url
        }
        
        logger.debug(f"Making API request to {self.RAPIDAPI_URL}")
        logger.debug(f"Payload: {payload}")
        
        request_time = datetime.now()
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
            async with self.session.post(
                self.RAPIDAPI_URL,
                json=payload,
                headers=headers,
                timeout=timeout
            ) as response:
                response_time = datetime.now()
                duration = (response_time - request_time).total_seconds()
                
                logger.debug(f"API response received in {duration:.2f}s - Status: {response.status}")
                
                # Read response body
                response_text = await response.text()
                
                # Handle different status codes
                if response.status == 200:
                    try:
                        result = await response.json()
                        logger.debug(f"API response: {result}")
                        return result
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        logger.debug(f"Response text: {response_text}")
                        raise KasadaSolverError(f"Invalid JSON response: {e}")
                
                elif response.status == 401:
                    raise InvalidAPIKeyError("Invalid or missing RapidAPI key")
                
                elif response.status == 429:
                    raise RateLimitError("RapidAPI rate limit exceeded. Please upgrade or wait.")
                
                elif response.status == 403:
                    raise InvalidAPIKeyError("API key does not have access to this endpoint")
                
                else:
                    error_msg = f"API returned status {response.status}: {response_text}"
                    logger.error(error_msg)
                    raise KasadaSolverError(error_msg)
                    
        except asyncio.TimeoutError:
            logger.error(f"Request timed out after {self.TIMEOUT_SECONDS}s")
            raise
        
        except aiohttp.ClientError as e:
            logger.error(f"Client error during API request: {e}")
            raise

    async def close(self):
        """Close the HTTP session and cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("KasadaSolver session closed")

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
