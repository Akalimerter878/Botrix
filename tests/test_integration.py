"""
Integration tests for complete account creation workflow

Tests the entire flow with mocked external services
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from workers.account_creator import KickAccountCreator
from workers.kasada_solver import KasadaSolver
from workers.email_handler import HotmailPool, EmailVerifier
from workers.config import Config


@pytest.fixture
def temp_integration_dir(tmp_path):
    """Create temporary directory structure for integration tests"""
    # Create directories
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    # Create pool file
    pool_file = shared_dir / "livelive.txt"
    pool_file.write_text(
        "test1@hotmail.com:password123\n"
        "test2@outlook.com:password456\n"
        "test3@live.com:password789\n",
        encoding='utf-8'
    )
    
    # Create empty kicks file
    kicks_file = shared_dir / "kicks.json"
    kicks_file.write_text("[]", encoding='utf-8')
    
    return {
        'root': tmp_path,
        'shared': shared_dir,
        'logs': logs_dir,
        'pool_file': str(pool_file),
        'kicks_file': str(kicks_file)
    }


@pytest.fixture
def mock_config():
    """Create mock configuration"""
    config = Config()
    config.RAPIDAPI_KEY = "test_api_key"
    config.IMAP_SERVER = "imap.test.com"
    config.IMAP_PORT = 993
    return config


@pytest.mark.asyncio
async def test_integration_dry_run_success(temp_integration_dir, mock_config):
    """Test complete dry-run workflow with all mocks"""
    
    # Initialize components
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    
    # Mock Kasada solver (test mode)
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    
    # Create account creator
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        config=mock_config,
        output_file=temp_integration_dir['kicks_file']
    )
    
    # Mock IMAP connection
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        # Mock email search returning verification code
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b'1'])
        
        # Create mock email with verification code
        from email.mime.text import MIMEText
        msg = MIMEText("Your verification code is 123456")
        msg['Subject'] = "Kick Verification"
        msg['From'] = "noreply@email.kick.com"
        
        raw_email = msg.as_bytes()
        mock_connection.fetch.return_value = ('OK', [(b'1', raw_email)])
        
        # Mock HTTP requests
        with patch('aiohttp.ClientSession.request') as mock_request:
            # Mock send verification email
            mock_resp_send = AsyncMock()
            mock_resp_send.status = 200
            mock_resp_send.json = AsyncMock(return_value={"success": True})
            
            # Mock verify code
            mock_resp_verify = AsyncMock()
            mock_resp_verify.status = 200
            mock_resp_verify.json = AsyncMock(return_value={"token": "test_token_123"})
            
            # Mock register account
            mock_resp_register = AsyncMock()
            mock_resp_register.status = 200
            mock_resp_register.json = AsyncMock(return_value={
                "id": 12345,
                "username": "testuser",
                "email": "test1@hotmail.com"
            })
            
            # Setup side effects for different endpoints
            async def request_side_effect(*args, **kwargs):
                url = args[1] if len(args) > 1 else kwargs.get('url', '')
                
                if 'send/email' in url:
                    return mock_resp_send
                elif 'verify/email' in url:
                    return mock_resp_verify
                elif 'register' in url:
                    return mock_resp_register
                
                # Default response
                mock_default = AsyncMock()
                mock_default.status = 200
                mock_default.json = AsyncMock(return_value={})
                return mock_default
            
            mock_request.side_effect = request_side_effect
            
            # Create account
            result = await creator.create_account(
                username="testuser",
                password="testpass123"
            )
            
            # Verify success
            assert result['success'] is True
            assert result['username'] == "testuser"
            assert result['email'] == "test1@hotmail.com"
            assert result['verification_code'] == "123456"
            
            # Verify email was marked as used
            assert "test1@hotmail.com" in pool.used_emails
            
            # Verify account was saved
            with open(temp_integration_dir['kicks_file'], 'r') as f:
                saved_accounts = json.load(f)
            
            assert len(saved_accounts) == 1
            assert saved_accounts[0]['username'] == "testuser"
    
    await creator.close()
    await kasada_solver.close()


@pytest.mark.asyncio
async def test_integration_kasada_failure(temp_integration_dir):
    """Test workflow when Kasada solver fails"""
    
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    
    # Create solver that will fail
    kasada_solver = KasadaSolver(api_key="test", test_mode=False)
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        output_file=temp_integration_dir['kicks_file']
    )
    
    # Mock Kasada API to fail
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.json = AsyncMock(return_value={"error": "Invalid API key"})
        mock_post.return_value.__aenter__.return_value = mock_resp
        
        # Attempt to create account
        result = await creator.create_account()
        
        # Should fail
        assert result['success'] is False
        assert 'Kasada' in result['error'] or 'kasada' in result['error'].lower()
        
        # Email should be marked as failed
        assert len(pool.failed_emails) > 0
    
    await creator.close()
    await kasada_solver.close()


@pytest.mark.asyncio
async def test_integration_email_verification_timeout(temp_integration_dir):
    """Test workflow when email verification times out"""
    
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        output_file=temp_integration_dir['kicks_file']
    )
    
    # Mock IMAP to never find email
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        # No emails found
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b''])
        
        # Mock send verification email success
        with patch('aiohttp.ClientSession.request') as mock_request:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"success": True})
            mock_request.return_value = mock_resp
            
            # Attempt to create account (will timeout waiting for email)
            result = await creator.create_account()
            
            # Should fail due to no email
            assert result['success'] is False
            assert 'Email verification' in result['error'] or 'No email' in result['error']
    
    await creator.close()
    await kasada_solver.close()


@pytest.mark.asyncio
async def test_integration_registration_failure(temp_integration_dir):
    """Test workflow when registration fails (e.g., username taken)"""
    
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        output_file=temp_integration_dir['kicks_file']
    )
    
    # Mock IMAP
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        # Mock email found
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b'1'])
        
        from email.mime.text import MIMEText
        msg = MIMEText("Code: 999888")
        msg['From'] = "noreply@email.kick.com"
        mock_connection.fetch.return_value = ('OK', [(b'1', msg.as_bytes())])
        
        # Mock HTTP requests
        with patch('aiohttp.ClientSession.request') as mock_request:
            async def request_side_effect(*args, **kwargs):
                url = args[1] if len(args) > 1 else kwargs.get('url', '')
                
                mock_resp = AsyncMock()
                
                if 'send/email' in url:
                    mock_resp.status = 200
                    mock_resp.json = AsyncMock(return_value={"success": True})
                elif 'verify/email' in url:
                    mock_resp.status = 200
                    mock_resp.json = AsyncMock(return_value={"token": "test_token"})
                elif 'register' in url:
                    # Registration fails
                    mock_resp.status = 400
                    mock_resp.json = AsyncMock(return_value={
                        "error": "Username already taken"
                    })
                else:
                    mock_resp.status = 200
                    mock_resp.json = AsyncMock(return_value={})
                
                return mock_resp
            
            mock_request.side_effect = request_side_effect
            
            result = await creator.create_account(username="taken_username")
            
            # Should fail
            assert result['success'] is False
            assert 'Registration' in result['error'] or 'registration' in result['error'].lower()
            
            # Email should be marked as used (was verified but registration failed)
            assert len(pool.used_emails) > 0
    
    await creator.close()
    await kasada_solver.close()


@pytest.mark.asyncio
async def test_integration_multiple_accounts(temp_integration_dir):
    """Test creating multiple accounts sequentially"""
    
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        output_file=temp_integration_dir['kicks_file']
    )
    
    results = []
    
    # Mock all external services
    with patch('imaplib.IMAP4_SSL') as mock_imap, \
         patch('aiohttp.ClientSession.request') as mock_request:
        
        # Setup mocks
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b'1'])
        
        from email.mime.text import MIMEText
        msg = MIMEText("Code: 123456")
        msg['From'] = "noreply@email.kick.com"
        mock_connection.fetch.return_value = ('OK', [(b'1', msg.as_bytes())])
        
        # Mock HTTP success
        async def request_side_effect(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get('url', '')
            mock_resp = AsyncMock()
            
            if 'verify/email' in url:
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"token": "token123"})
            elif 'register' in url:
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"id": 1, "username": "user"})
            else:
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"success": True})
            
            return mock_resp
        
        mock_request.side_effect = request_side_effect
        
        # Create 3 accounts
        for i in range(3):
            result = await creator.create_account()
            results.append(result)
        
        # All should succeed
        assert all(r['success'] for r in results)
        assert len(results) == 3
        
        # All should have different emails
        emails = [r['email'] for r in results]
        assert len(set(emails)) == 3
        
        # Pool should have 3 used emails
        assert len(pool.used_emails) == 3
        
        # All accounts should be saved
        with open(temp_integration_dir['kicks_file'], 'r') as f:
            saved_accounts = json.load(f)
        assert len(saved_accounts) == 3
    
    await creator.close()
    await kasada_solver.close()


@pytest.mark.asyncio
async def test_integration_error_propagation(temp_integration_dir):
    """Test that errors propagate correctly through the stack"""
    
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        output_file=temp_integration_dir['kicks_file']
    )
    
    # Mock IMAP to raise exception
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_imap.side_effect = Exception("Network error")
        
        # Should handle exception gracefully
        result = await creator.create_account()
        
        assert result['success'] is False
        assert 'error' in result
        assert 'message' in result
    
    await creator.close()
    await kasada_solver.close()


@pytest.mark.asyncio
async def test_integration_pool_exhaustion(temp_integration_dir):
    """Test behavior when email pool is exhausted"""
    
    # Create pool with only 1 email
    pool_file = temp_integration_dir['shared'] / "small_pool.txt"
    pool_file.write_text("single@email.com:pass123\n", encoding='utf-8')
    
    pool = HotmailPool(pool_file=str(pool_file))
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        output_file=temp_integration_dir['kicks_file']
    )
    
    with patch('imaplib.IMAP4_SSL') as mock_imap, \
         patch('aiohttp.ClientSession.request') as mock_request:
        
        # Setup successful mocks
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b'1'])
        
        from email.mime.text import MIMEText
        msg = MIMEText("Code: 123456")
        msg['From'] = "noreply@email.kick.com"
        mock_connection.fetch.return_value = ('OK', [(b'1', msg.as_bytes())])
        
        async def request_success(*args, **kwargs):
            url = args[1] if len(args) > 1 else kwargs.get('url', '')
            mock_resp = AsyncMock()
            if 'verify' in url:
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"token": "t"})
            else:
                mock_resp.status = 200
                mock_resp.json = AsyncMock(return_value={"success": True})
            return mock_resp
        
        mock_request.side_effect = request_success
        
        # First account should succeed
        result1 = await creator.create_account()
        assert result1['success'] is True
        
        # Second account should fail (pool empty)
        result2 = await creator.create_account()
        assert result2['success'] is False
    
    await creator.close()
    await kasada_solver.close()


def test_integration_components_initialized_correctly(temp_integration_dir):
    """Test that all components are properly initialized"""
    
    pool = HotmailPool(pool_file=temp_integration_dir['pool_file'])
    kasada_solver = KasadaSolver(api_key="test", test_mode=True)
    config = Config()
    
    creator = KickAccountCreator(
        email_pool=pool,
        kasada_solver=kasada_solver,
        config=config,
        output_file=temp_integration_dir['kicks_file']
    )
    
    # Verify all components are set
    assert creator.email_pool is not None
    assert creator.kasada_solver is not None
    assert creator.config is not None
    assert creator.output_file is not None
    
    # Verify endpoints are configured
    assert creator.SEND_CODE_ENDPOINT is not None
    assert creator.VERIFY_CODE_ENDPOINT is not None
    assert creator.REGISTER_ENDPOINT is not None
    
    # Verify rate limiting constants
    assert creator.REQUEST_DELAY > 0
    assert creator.RETRY_ATTEMPTS > 0
