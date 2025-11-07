"""
Shared pytest fixtures and configuration
"""

import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock
from workers.config import Config


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables for testing"""
    monkeypatch.setenv("RAPIDAPI_KEY", "test_api_key_12345")
    monkeypatch.setenv("IMAP_SERVER", "imap.test.com")
    monkeypatch.setenv("IMAP_PORT", "993")
    monkeypatch.setenv("POOL_FILE", "shared/livelive.txt")
    monkeypatch.setenv("OUTPUT_FILE", "shared/kicks.json")


@pytest.fixture
def test_config(mock_env_vars):
    """Create test configuration"""
    config = Config()
    config.RAPIDAPI_KEY = "test_api_key_12345"
    config.IMAP_SERVER = "imap.test.com"
    config.IMAP_PORT = 993
    return config


@pytest.fixture
def temp_email_pool(tmp_path):
    """Create temporary email pool file"""
    pool_file = tmp_path / "test_pool.txt"
    pool_file.write_text(
        "test1@hotmail.com:password123\n"
        "test2@outlook.com:password456\n"
        "test3@live.com:password789\n"
        "test4@hotmail.com:password000\n"
        "test5@outlook.com:password111\n",
        encoding='utf-8'
    )
    return str(pool_file)


@pytest.fixture
def temp_output_file(tmp_path):
    """Create temporary output file for accounts"""
    output_file = tmp_path / "test_kicks.json"
    output_file.write_text("[]", encoding='utf-8')
    return str(output_file)


@pytest.fixture
def mock_imap_connection():
    """Create mock IMAP connection"""
    mock_conn = MagicMock()
    mock_conn.select.return_value = ('OK', [])
    mock_conn.search.return_value = ('OK', [b''])
    mock_conn.fetch.return_value = ('OK', [])
    mock_conn.close.return_value = ('OK', [])
    mock_conn.logout.return_value = ('BYE', [])
    return mock_conn


@pytest.fixture
def mock_verification_email():
    """Create mock verification email"""
    from email.mime.text import MIMEText
    
    msg = MIMEText("Your Kick verification code is: 123456\n\nPlease enter this code to verify your account.")
    msg['Subject'] = "Kick.com Email Verification"
    msg['From'] = "noreply@email.kick.com"
    msg['To'] = "test@hotmail.com"
    
    return msg.as_bytes()


@pytest.fixture
def sample_emails():
    """Sample email pool data"""
    return [
        ("user1@hotmail.com", "pass123"),
        ("user2@outlook.com", "pass456"),
        ("user3@live.com", "pass789"),
    ]


@pytest.fixture
def mock_kasada_response():
    """Mock successful Kasada API response"""
    return {
        "x-kpsdk-ct": "mock-ct-token-12345",
        "x-kpsdk-cd": "mock-cd-token-67890",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }


@pytest.fixture
def mock_kasada_error_response():
    """Mock error Kasada API response"""
    return {
        "error": "Invalid API key",
        "code": 401
    }


@pytest.fixture
def mock_kick_api_responses():
    """Mock Kick.com API responses"""
    return {
        "send_code": {
            "success": True,
            "message": "Verification code sent"
        },
        "verify_code": {
            "success": True,
            "token": "verification_token_abc123"
        },
        "register": {
            "id": 12345,
            "username": "testuser",
            "email": "test@hotmail.com",
            "created_at": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests"""
    # If you have any singletons, reset them here
    yield
    # Cleanup after test


@pytest.fixture
def suppress_logging(caplog):
    """Suppress logging output during tests"""
    import logging
    caplog.set_level(logging.CRITICAL)
    return caplog


# Async fixtures for aiohttp mocking
@pytest.fixture
def mock_aiohttp_session():
    """Create mock aiohttp session"""
    from unittest.mock import AsyncMock
    
    session = MagicMock()
    
    # Mock context manager
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    
    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={})
    mock_response.text = AsyncMock(return_value="")
    
    # Mock methods
    session.get = AsyncMock(return_value=mock_response)
    session.post = AsyncMock(return_value=mock_response)
    session.put = AsyncMock(return_value=mock_response)
    session.delete = AsyncMock(return_value=mock_response)
    
    return session


@pytest.fixture
def mock_successful_account_creation():
    """Mock data for successful account creation"""
    return {
        "username": "test_user_123",
        "password": "SecurePass123!",
        "email": "test@hotmail.com",
        "email_password": "email_pass_123",
        "verification_code": "123456",
        "success": True
    }


# Markers for different test categories
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for multiple components"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )
    config.addinivalue_line(
        "markers", "network: Tests that require network access (should be mocked)"
    )
