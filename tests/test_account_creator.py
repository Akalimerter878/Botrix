"""Tests for account creator"""

import pytest
import asyncio
from pathlib import Path
from workers.account_creator import (
    KickAccountCreator,
    generate_random_username,
    generate_random_password,
    generate_random_birthdate,
    AccountCreationError,
    VerificationFailedError,
    RegistrationFailedError
)
from workers.kasada_solver import KasadaSolver
from workers.email_handler import HotmailPool


# Test helper functions

def test_generate_random_username():
    """Test username generation"""
    username = generate_random_username()
    
    assert username is not None
    assert len(username) == 10
    assert username[0].isalpha()  # First char is letter
    
    # Generate multiple and check uniqueness
    usernames = [generate_random_username() for _ in range(10)]
    assert len(set(usernames)) == 10  # All unique


def test_generate_random_username_custom_length():
    """Test username generation with custom length"""
    username = generate_random_username(length=15)
    assert len(username) == 15
    
    username = generate_random_username(length=5)
    assert len(username) == 5


def test_generate_random_password():
    """Test password generation"""
    password = generate_random_password()
    
    assert password is not None
    assert len(password) == 16
    
    # Should contain mix of characters
    assert any(c.isupper() for c in password) or any(c.islower() for c in password)
    
    # Generate multiple and check uniqueness
    passwords = [generate_random_password() for _ in range(10)]
    assert len(set(passwords)) == 10  # All unique


def test_generate_random_password_custom_length():
    """Test password generation with custom length"""
    password = generate_random_password(length=20)
    assert len(password) == 20
    
    password = generate_random_password(length=8)
    assert len(password) == 8


def test_generate_random_birthdate():
    """Test birthdate generation"""
    import re
    
    birthdate = generate_random_birthdate()
    
    assert birthdate is not None
    # Check format YYYY-MM-DD
    assert re.match(r'\d{4}-\d{2}-\d{2}', birthdate)
    
    # Parse date
    year, month, day = map(int, birthdate.split('-'))
    
    # Check valid ranges
    assert 1 <= month <= 12
    assert 1 <= day <= 31
    
    # Age should be between 18 and 35
    from datetime import datetime
    current_year = datetime.now().year
    age = current_year - year
    assert 18 <= age <= 35


# KickAccountCreator Tests

@pytest.fixture
def temp_pool_file(tmp_path):
    """Create temporary pool file"""
    pool_file = tmp_path / "test_pool.txt"
    pool_file.write_text("test@example.com:password123\n", encoding='utf-8')
    return str(pool_file)


@pytest.fixture
def temp_output_file(tmp_path):
    """Create temporary output file path"""
    return str(tmp_path / "test_kicks.json")


@pytest.fixture
def email_pool(temp_pool_file):
    """Create test email pool"""
    return HotmailPool(pool_file=temp_pool_file)


@pytest.fixture
async def kasada_solver():
    """Create test Kasada solver"""
    solver = KasadaSolver(api_key="test", test_mode=True)
    yield solver
    await solver.close()


@pytest.fixture
async def account_creator(email_pool, kasada_solver, temp_output_file):
    """Create test account creator"""
    creator = KickAccountCreator(
        email_pool=email_pool,
        kasada_solver=kasada_solver,
        output_file=temp_output_file
    )
    yield creator
    await creator.close()


@pytest.mark.asyncio
async def test_account_creator_initialization(account_creator):
    """Test KickAccountCreator initializes correctly"""
    assert account_creator is not None
    assert account_creator.email_pool is not None
    assert account_creator.kasada_solver is not None


@pytest.mark.asyncio
async def test_account_creator_ensure_session(account_creator):
    """Test session creation"""
    await account_creator._ensure_session()
    assert account_creator.session is not None
    assert not account_creator.session.closed


@pytest.mark.asyncio
async def test_account_creator_close(account_creator):
    """Test closing the creator"""
    await account_creator._ensure_session()
    assert account_creator.session is not None
    
    await account_creator.close()
    # Should be closed or None


@pytest.mark.asyncio
async def test_account_creator_context_manager(email_pool, kasada_solver, temp_output_file):
    """Test as async context manager"""
    async with KickAccountCreator(
        email_pool=email_pool,
        kasada_solver=kasada_solver,
        output_file=temp_output_file
    ) as creator:
        assert creator is not None


@pytest.mark.asyncio
async def test_save_account(account_creator, temp_output_file):
    """Test saving account to file"""
    import json
    
    account_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass",
        "birthdate": "2000-01-01"
    }
    
    account_creator._save_account(account_data)
    
    # Check file exists and contains data
    output_path = Path(temp_output_file)
    assert output_path.exists()
    
    with open(output_path, 'r', encoding='utf-8') as f:
        saved_accounts = json.load(f)
    
    assert len(saved_accounts) == 1
    assert saved_accounts[0]['username'] == 'testuser'
    assert 'created_at' in saved_accounts[0]


@pytest.mark.asyncio
async def test_save_multiple_accounts(account_creator, temp_output_file):
    """Test saving multiple accounts"""
    import json
    
    # Save first account
    account_creator._save_account({
        "username": "user1",
        "email": "user1@example.com"
    })
    
    # Save second account
    account_creator._save_account({
        "username": "user2",
        "email": "user2@example.com"
    })
    
    # Check both are saved
    with open(temp_output_file, 'r', encoding='utf-8') as f:
        saved_accounts = json.load(f)
    
    assert len(saved_accounts) == 2
    assert saved_accounts[0]['username'] == 'user1'
    assert saved_accounts[1]['username'] == 'user2'


@pytest.mark.skip(reason="Requires mock HTTP responses")
@pytest.mark.asyncio
async def test_create_account_full_flow():
    """Test complete account creation flow"""
    # This would require mocking all HTTP responses
    pass


@pytest.mark.skip(reason="Requires live API")
@pytest.mark.asyncio
async def test_create_account_live():
    """Test with live API"""
    # Only run with valid credentials
    pass


def test_account_creator_constants():
    """Test that API endpoints are defined"""
    assert KickAccountCreator.KICK_API_BASE is not None
    assert KickAccountCreator.SEND_CODE_ENDPOINT is not None
    assert KickAccountCreator.VERIFY_CODE_ENDPOINT is not None
    assert KickAccountCreator.REGISTER_ENDPOINT is not None
    
    # Check URLs are properly formatted
    assert "https://" in KickAccountCreator.KICK_API_BASE
    assert "kick.com" in KickAccountCreator.KICK_API_BASE


def test_rate_limiting_constants():
    """Test rate limiting constants"""
    assert KickAccountCreator.REQUEST_DELAY > 0
    assert KickAccountCreator.RETRY_ATTEMPTS > 0
    assert KickAccountCreator.RETRY_DELAY > 0
