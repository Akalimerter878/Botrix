"""Comprehensive tests for Kasada solver with mocking"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp
from workers.kasada_solver import (
    KasadaSolver,
    KasadaSolverError,
    InvalidAPIKeyError,
    RateLimitError,
    TimeoutError
)


@pytest.fixture
def test_api_key():
    """Provide a test API key"""
    return "test_rapidapi_key_12345"


@pytest.fixture
def kasada_solver_test_mode(test_api_key):
    """Create a KasadaSolver instance in test mode"""
    return KasadaSolver(api_key=test_api_key, test_mode=True)


@pytest.fixture
def kasada_solver_live(test_api_key):
    """Create a KasadaSolver instance for live API calls"""
    return KasadaSolver(api_key=test_api_key, test_mode=False)


# Initialization Tests

@pytest.mark.asyncio
async def test_kasada_solver_initialization():
    """Test that KasadaSolver initializes correctly"""
    solver = KasadaSolver(api_key="test_key", test_mode=True)
    assert solver is not None
    assert solver.api_key == "test_key"
    assert solver.test_mode is True
    assert solver.session is None
    await solver.close()


@pytest.mark.asyncio
async def test_kasada_solver_initialization_no_key():
    """Test that KasadaSolver raises error without API key in live mode"""
    with pytest.raises(InvalidAPIKeyError):
        KasadaSolver(api_key="", test_mode=False)


def test_kasada_solver_test_mode_no_key_required():
    """Test that test mode doesn't require API key"""
    solver = KasadaSolver(api_key="", test_mode=True)
    assert solver.test_mode is True


# Test Mode Tests

@pytest.mark.asyncio
async def test_solve_challenge_test_mode(kasada_solver_test_mode):
    """Test Kasada challenge solving in test mode"""
    result = await kasada_solver_test_mode.solve(
        method="POST",
        fetch_url="https://kick.com/api/v1/signup/send/email"
    )
    
    assert result is not None
    assert isinstance(result, dict)
    assert "x-kpsdk-cd" in result
    assert "x-kpsdk-ct" in result
    assert "user-agent" in result
    assert "cookie" in result
    
    # Check values are mocked
    assert "mock" in result["x-kpsdk-cd"].lower()
    
    await kasada_solver_test_mode.close()


@pytest.mark.asyncio
async def test_solve_challenge_missing_url(kasada_solver_test_mode):
    """Test that solve raises error when URL is missing"""
    with pytest.raises(ValueError, match="fetch_url is required"):
        await kasada_solver_test_mode.solve(method="POST", fetch_url="")


@pytest.mark.asyncio
async def test_solve_challenge_different_methods(kasada_solver_test_mode):
    """Test solving with different HTTP methods"""
    methods = ["GET", "POST", "PUT", "DELETE"]
    
    for method in methods:
        result = await kasada_solver_test_mode.solve(
            method=method,
            fetch_url="https://kick.com/api/test"
        )
        assert result is not None
        assert isinstance(result, dict)
    
    await kasada_solver_test_mode.close()


# Context Manager Tests

@pytest.mark.asyncio
async def test_kasada_solver_context_manager(test_api_key):
    """Test KasadaSolver as async context manager"""
    async with KasadaSolver(api_key=test_api_key, test_mode=True) as solver:
        assert solver is not None
        result = await solver.solve(
            method="POST",
            fetch_url="https://kick.com/api/v1/test"
        )
        assert result is not None


# Rate Limiting Tests

@pytest.mark.asyncio
async def test_rate_limiting(kasada_solver_test_mode):
    """Test that rate limiting works correctly"""
    start_time = time.time()
    
    # Make 3 consecutive requests
    for i in range(3):
        await kasada_solver_test_mode.solve(
            method="POST",
            fetch_url=f"https://kick.com/api/v1/test{i}"
        )
    
    elapsed_time = time.time() - start_time
    
    # Should take at least 2 seconds (3 requests with 1 sec delay = 2 sec minimum)
    assert elapsed_time >= 2.0
    
    await kasada_solver_test_mode.close()


@pytest.mark.asyncio
async def test_rate_limit_delay_enforcement(kasada_solver_test_mode):
    """Test rate limit delay is enforced between requests"""
    # First request
    await kasada_solver_test_mode.solve(
        method="POST",
        fetch_url="https://kick.com/api/test1"
    )
    
    first_request_time = kasada_solver_test_mode.last_request_time
    
    # Wait a bit
    await asyncio.sleep(0.5)
    
    # Second request should be delayed
    start = time.time()
    await kasada_solver_test_mode.solve(
        method="POST",
        fetch_url="https://kick.com/api/test2"
    )
    elapsed = time.time() - start
    
    # Should have waited at least 0.5s to reach 1s total
    assert elapsed >= 0.5
    
    await kasada_solver_test_mode.close()


# Mock API Response Tests

@pytest.mark.asyncio
async def test_make_api_request_success():
    """Test successful API request with mocked response"""
    solver = KasadaSolver(api_key="test_key", test_mode=False)
    
    mock_response = {
        "x-kpsdk-cd": "test-cd-token",
        "x-kpsdk-ct": "test-ct-token",
        "user-agent": "test-agent"
    }
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        # Create mock response
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        result = await solver._make_api_request(
            "POST",
            "https://api.test.com",
            {"X-RapidAPI-Key": "test"}
        )
        
        status, data = result
        assert status == 200
        assert data == mock_response
    
    await solver.close()


@pytest.mark.asyncio
async def test_make_api_request_invalid_api_key():
    """Test API request with invalid API key (401)"""
    solver = KasadaSolver(api_key="invalid_key", test_mode=False)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.json = AsyncMock(return_value={"error": "Invalid API key"})
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        result = await solver._make_api_request(
            "POST",
            "https://api.test.com",
            {"X-RapidAPI-Key": "invalid"}
        )
        
        status, data = result
        assert status == 401
    
    await solver.close()


@pytest.mark.asyncio
async def test_make_api_request_rate_limit():
    """Test API request with rate limit (429)"""
    solver = KasadaSolver(api_key="test_key", test_mode=False)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.json = AsyncMock(return_value={"error": "Rate limit exceeded"})
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        result = await solver._make_api_request(
            "POST",
            "https://api.test.com",
            {"X-RapidAPI-Key": "test"}
        )
        
        status, data = result
        assert status == 429
    
    await solver.close()


# Retry Logic Tests

@pytest.mark.asyncio
async def test_solve_with_retry_on_server_error():
    """Test that solver retries on server errors (5xx)"""
    solver = KasadaSolver(api_key="test_key", test_mode=False)
    
    call_count = 0
    
    async def mock_post_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        mock_resp = AsyncMock()
        
        if call_count < 2:
            # First call fails with 500
            mock_resp.status = 500
            mock_resp.json = AsyncMock(return_value={"error": "Server error"})
        else:
            # Second call succeeds
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={
                "x-kpsdk-cd": "success-token"
            })
        
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_resp
        return mock_context
    
    with patch('aiohttp.ClientSession.post', side_effect=mock_post_side_effect):
        result = await solver.solve(
            method="POST",
            fetch_url="https://kick.com/api/test"
        )
        
        # Should have retried and succeeded
        assert result is not None
        assert call_count == 2
    
    await solver.close()


@pytest.mark.asyncio
async def test_solve_max_retries_exceeded():
    """Test that solver fails after max retries"""
    solver = KasadaSolver(api_key="test_key", test_mode=False)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        # Always return server error
        mock_resp = AsyncMock()
        mock_resp.status = 500
        mock_resp.json = AsyncMock(return_value={"error": "Server error"})
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        with pytest.raises(KasadaSolverError):
            await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/test"
            )
    
    await solver.close()


@pytest.mark.asyncio
async def test_solve_no_retry_on_client_error():
    """Test that solver doesn't retry on client errors (4xx)"""
    solver = KasadaSolver(api_key="test_key", test_mode=False)
    
    call_count = 0
    
    async def count_calls(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = AsyncMock()
        mock_resp.status = 400
        mock_resp.json = AsyncMock(return_value={"error": "Bad request"})
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_resp
        return mock_context
    
    with patch('aiohttp.ClientSession.post', side_effect=count_calls):
        with pytest.raises(KasadaSolverError):
            await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/test"
            )
        
        # Should only call once (no retry on 4xx)
        assert call_count == 1
    
    await solver.close()


# Timeout Tests

@pytest.mark.asyncio
async def test_solve_timeout_error():
    """Test handling of timeout errors"""
    solver = KasadaSolver(api_key="test_key", test_mode=False)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        # Simulate timeout
        mock_post.side_effect = asyncio.TimeoutError()
        
        with pytest.raises((TimeoutError, KasadaSolverError)):
            await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/test"
            )
    
    await solver.close()


# Error Handling Tests

@pytest.mark.asyncio
async def test_solve_invalid_api_key_error():
    """Test handling of invalid API key (401)"""
    solver = KasadaSolver(api_key="invalid", test_mode=False)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.json = AsyncMock(return_value={"error": "Unauthorized"})
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        with pytest.raises(InvalidAPIKeyError):
            await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/test"
            )
    
    await solver.close()


@pytest.mark.asyncio
async def test_solve_rate_limit_error():
    """Test handling of rate limit (429)"""
    solver = KasadaSolver(api_key="test", test_mode=False)
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 429
        mock_resp.json = AsyncMock(return_value={"error": "Too many requests"})
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        with pytest.raises(RateLimitError):
            await solver.solve(
                method="POST",
                fetch_url="https://kick.com/api/test"
            )
    
    await solver.close()


@pytest.mark.asyncio
async def test_kasada_solver_close(kasada_solver_test_mode):
    """Test that KasadaSolver closes properly"""
    await kasada_solver_test_mode._ensure_session()
    assert kasada_solver_test_mode.session is not None
    
    await kasada_solver_test_mode.close()
    # Should be able to call close multiple times without error
    await kasada_solver_test_mode.close()


# Live API Tests (Skipped by default)

@pytest.mark.skip(reason="Requires valid RapidAPI key")
@pytest.mark.asyncio
async def test_solve_challenge_live():
    """Test Kasada challenge solving with live API"""
    import os
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        pytest.skip("RAPIDAPI_KEY not set")
    
    async with KasadaSolver(api_key=api_key, test_mode=False) as solver:
        result = await solver.solve(
            method="POST",
            fetch_url="https://kick.com/api/v1/signup/send/email"
        )
        
        assert result is not None
        assert isinstance(result, dict)
