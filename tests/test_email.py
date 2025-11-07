"""Comprehensive tests for email handler with mocking"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import imaplib
import email
from workers.email_handler import (
    EmailVerifier,
    HotmailPool,
    EmailVerificationError,
    IMAPLoginError,
    NoEmailReceivedError,
    EmailPoolEmptyError,
    MalformedEmailFormatError
)


@pytest.fixture
def test_email_credentials():
    """Provide test email credentials"""
    return ("test@example.com", "test_password")


@pytest.fixture
def email_verifier(test_email_credentials):
    """Create an EmailVerifier instance"""
    email_address, password = test_email_credentials
    return EmailVerifier(
        email_address=email_address,
        password=password,
        imap_server="imap.test.com",
        imap_port=993
    )


@pytest.fixture
def temp_pool_file(tmp_path):
    """Create a temporary pool file for testing"""
    pool_file = tmp_path / "test_livelive.txt"
    content = """# Test email pool
test1@hotmail.com:password123
test2@outlook.com:password456
test3@live.com:password789
invalid_email_no_colon
not-an-email:password
test4@gmail.com:password000
"""
    pool_file.write_text(content, encoding='utf-8')
    return str(pool_file)


@pytest.fixture
def empty_pool_file(tmp_path):
    """Create an empty pool file"""
    pool_file = tmp_path / "empty_pool.txt"
    pool_file.write_text("", encoding='utf-8')
    return str(pool_file)


@pytest.fixture
def malformed_pool_file(tmp_path):
    """Create a malformed pool file"""
    pool_file = tmp_path / "malformed_pool.txt"
    pool_file.write_text("invalid_line_without_colon\n", encoding='utf-8')
    return str(pool_file)


# EmailVerifier Tests

def test_email_verifier_initialization(email_verifier):
    """Test that EmailVerifier initializes correctly"""
    assert email_verifier is not None
    assert email_verifier.email_address == "test@example.com"
    assert email_verifier.password == "test_password"
    assert email_verifier.imap_server == "imap.test.com"
    assert email_verifier.imap_port == 993
    assert email_verifier.imap_connection is None


def test_email_verifier_disconnect_when_not_connected(email_verifier):
    """Test that disconnect works even when not connected"""
    # Should not raise an error
    email_verifier.disconnect()
    assert email_verifier.imap_connection is None


def test_email_verifier_decode_header(email_verifier):
    """Test header decoding"""
    # Simple ASCII header
    result = email_verifier._decode_header("Test Subject")
    assert result == "Test Subject"
    
    # Empty header
    result = email_verifier._decode_header("")
    assert result == ""


def test_email_verifier_extract_code_from_text(email_verifier):
    """Test verification code extraction from text"""
    # Test various formats
    test_cases = [
        ("Your verification code is: 123456", "123456"),
        ("Code: 9876", "9876"),
        ("Verification 54321", "54321"),
        ("Confirm with code 11111", "11111"),
        ("Your code is 88888", "88888"),
        ("Random text without code", None),
        ("", None),
    ]
    
    for text, expected in test_cases:
        result = email_verifier._extract_code_from_text(text)
        assert result == expected, f"Failed for text: {text}"


@pytest.mark.skip(reason="Requires actual IMAP server")
def test_email_verifier_connect_live():
    """Test connection to live IMAP server"""
    # This would require actual credentials
    pass


@pytest.mark.skip(reason="Requires actual IMAP server")
@pytest.mark.asyncio
async def test_email_verifier_get_verification_code_live():
    """Test getting verification code from live server"""
    # This would require actual credentials and verification email
    pass


@pytest.mark.asyncio
async def test_email_verifier_context_manager(test_email_credentials):
    """Test EmailVerifier as async context manager"""
    email_address, password = test_email_credentials
    
    # This will fail to connect, but should handle cleanup properly
    verifier = EmailVerifier(
        email_address=email_address,
        password=password,
        imap_server="imap.test.com"
    )
    
    # Test that __aexit__ works even if connection fails
    try:
        async with verifier:
            pass
    except IMAPLoginError:
        # Expected to fail with fake credentials
        pass
    
    # Connection should be None after context exit
    assert verifier.imap_connection is None


# HotmailPool Tests

def test_hotmail_pool_initialization(temp_pool_file):
    """Test HotmailPool initialization"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    assert pool is not None
    assert len(pool.available_emails) > 0
    assert len(pool.used_emails) == 0
    assert len(pool.failed_emails) == 0


def test_hotmail_pool_load_emails(temp_pool_file):
    """Test loading emails from file"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    # Should load valid emails (test1, test2, test3, test4)
    # Should skip invalid_email_no_colon and not-an-email
    assert len(pool.available_emails) == 4
    
    emails = [e[0] for e in pool.available_emails]
    assert "test1@hotmail.com" in emails
    assert "test2@outlook.com" in emails
    assert "test3@live.com" in emails
    assert "test4@gmail.com" in emails


def test_hotmail_pool_get_next_email(temp_pool_file):
    """Test getting next email from pool"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    email, password = pool.get_next_email()
    
    assert email is not None
    assert password is not None
    assert '@' in email
    assert len(password) > 0


def test_hotmail_pool_mark_as_used(temp_pool_file):
    """Test marking email as used"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    initial_count = len(pool.available_emails)
    email, password = pool.get_next_email()
    
    pool.mark_as_used(email)
    
    assert email in pool.used_emails
    assert len(pool.available_emails) == initial_count - 1
    
    # Should not be in available list anymore
    available_emails = [e[0] for e in pool.available_emails]
    assert email not in available_emails


def test_hotmail_pool_mark_as_failed(temp_pool_file):
    """Test marking email as failed"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    initial_count = len(pool.available_emails)
    email, password = pool.get_next_email()
    
    pool.mark_as_failed(email)
    
    assert email in pool.failed_emails
    assert len(pool.available_emails) == initial_count - 1
    
    # Should not be in available list anymore
    available_emails = [e[0] for e in pool.available_emails]
    assert email not in available_emails


def test_hotmail_pool_empty_error(temp_pool_file):
    """Test error when pool is empty"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    # Mark all emails as used
    while pool.available_emails:
        email, _ = pool.get_next_email()
        pool.mark_as_used(email)
    
    # Should raise error when trying to get email from empty pool
    with pytest.raises(EmailPoolEmptyError):
        pool.get_next_email()


def test_hotmail_pool_get_stats(temp_pool_file):
    """Test getting pool statistics"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    stats = pool.get_stats()
    
    assert 'available' in stats
    assert 'used' in stats
    assert 'failed' in stats
    assert 'total' in stats
    
    assert stats['available'] == len(pool.available_emails)
    assert stats['used'] == 0
    assert stats['failed'] == 0


def test_hotmail_pool_len(temp_pool_file):
    """Test __len__ method"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    assert len(pool) == len(pool.available_emails)
    
    # Mark one as used
    email, _ = pool.get_next_email()
    pool.mark_as_used(email)
    
    assert len(pool) == len(pool.available_emails)


def test_hotmail_pool_reload(temp_pool_file):
    """Test reloading pool"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    initial_count = len(pool.available_emails)
    
    # Mark some as used
    email, _ = pool.get_next_email()
    pool.mark_as_used(email)
    
    assert len(pool.available_emails) < initial_count
    
    # Reload (used emails won't be reloaded)
    pool.reload()
    
    # Should still have emails, but not the used one
    assert len(pool.available_emails) > 0
    assert email not in [e[0] for e in pool.available_emails]


def test_hotmail_pool_empty_file(empty_pool_file):
    """Test with empty pool file"""
    pool = HotmailPool(pool_file=empty_pool_file)
    
    assert len(pool.available_emails) == 0
    
    with pytest.raises(EmailPoolEmptyError):
        pool.get_next_email()


def test_hotmail_pool_malformed_file(malformed_pool_file):
    """Test with malformed pool file"""
    with pytest.raises(MalformedEmailFormatError):
        HotmailPool(pool_file=malformed_pool_file)


def test_hotmail_pool_nonexistent_file(tmp_path):
    """Test with nonexistent file (should create it)"""
    pool_file = tmp_path / "nonexistent.txt"
    
    pool = HotmailPool(pool_file=str(pool_file))
    
    # Should create empty file
    assert Path(pool_file).exists()
    assert len(pool.available_emails) == 0


def test_hotmail_pool_comments_and_blank_lines(tmp_path):
    """Test that comments and blank lines are ignored"""
    pool_file = tmp_path / "pool_with_comments.txt"
    content = """
# This is a comment
test1@example.com:pass1

# Another comment
test2@example.com:pass2

"""
    pool_file.write_text(content, encoding='utf-8')
    
    pool = HotmailPool(pool_file=str(pool_file))
    
    assert len(pool.available_emails) == 2


# Mock IMAP Tests

@pytest.mark.asyncio
async def test_email_verifier_connect_with_mock():
    """Test IMAP connection with mocked server"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password123",
        imap_server="imap.test.com",
        imap_port=993
    )
    
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        verifier.connect()
        
        # Verify connection was made
        mock_imap.assert_called_once_with("imap.test.com", 993)
        mock_connection.login.assert_called_once_with("test@example.com", "password123")
        
        assert verifier.imap_connection is not None
        
        verifier.disconnect()


@pytest.mark.asyncio
async def test_email_verifier_connect_failure():
    """Test IMAP connection failure"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="wrong_password",
        imap_server="imap.test.com"
    )
    
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_imap.side_effect = imaplib.IMAP4.error("Login failed")
        
        with pytest.raises(IMAPLoginError):
            verifier.connect()


@pytest.mark.asyncio
async def test_email_verifier_extract_code_from_email_subject():
    """Test extracting verification code from email subject"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password"
    )
    
    # Create mock email message
    mock_msg = MagicMock()
    mock_msg.get.return_value = "Your verification code is: 123456"
    mock_msg.is_multipart.return_value = False
    mock_msg.get_payload.return_value = b"Email body"
    
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        # Mock email search
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b'1'])
        
        # Mock email fetch
        raw_email = b"From: noreply@email.kick.com\nSubject: Your verification code is: 123456\n\nBody"
        mock_connection.fetch.return_value = ('OK', [(b'1', raw_email)])
        
        verifier.connect()
        code = verifier._search_verification_email()
        
        assert code == "123456"
        
        verifier.disconnect()


@pytest.mark.asyncio
async def test_email_verifier_get_verification_code_with_mock():
    """Test getting verification code with mocked IMAP"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password"
    )
    
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        # Mock successful search
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b'1'])
        
        # Create email with verification code
        from email.mime.text import MIMEText
        msg = MIMEText("Your verification code is 654321")
        msg['Subject'] = "Kick Verification"
        msg['From'] = "noreply@email.kick.com"
        
        raw_email = msg.as_bytes()
        mock_connection.fetch.return_value = ('OK', [(b'1', raw_email)])
        
        verifier.connect()
        
        # Mock the search to return immediately
        with patch.object(verifier, '_search_verification_email', return_value="654321"):
            code = await verifier.get_verification_code(timeout=5, poll_interval=1)
            assert code == "654321"
        
        verifier.disconnect()


@pytest.mark.asyncio
async def test_email_verifier_timeout():
    """Test verification code timeout"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password"
    )
    
    with patch('imaplib.IMAP4_SSL') as mock_imap:
        mock_connection = MagicMock()
        mock_imap.return_value = mock_connection
        
        # Mock no emails found
        mock_connection.select.return_value = ('OK', [])
        mock_connection.search.return_value = ('OK', [b''])
        
        verifier.connect()
        
        # Should timeout after specified time
        with pytest.raises(NoEmailReceivedError):
            await verifier.get_verification_code(timeout=2, poll_interval=1)
        
        verifier.disconnect()


def test_email_verifier_extract_code_patterns():
    """Test various code extraction patterns"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password"
    )
    
    test_cases = [
        ("Your code: 123456", "123456"),
        ("Verification code 987654", "987654"),
        ("Code is: 111222", "111222"),
        ("Your verification code is: 555666", "555666"),
        ("Confirm with 999888", "999888"),
        ("Random text 12345678", "12345678"),  # 8 digits
        ("Code: 1234", "1234"),  # 4 digits
        ("No code here", None),
        ("", None),
    ]
    
    for text, expected in test_cases:
        result = verifier._extract_code_from_text(text)
        assert result == expected, f"Failed for: {text}"


@pytest.mark.asyncio
async def test_email_verifier_decode_header():
    """Test email header decoding"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password"
    )
    
    # Test simple header
    result = verifier._decode_header("Test Subject")
    assert result == "Test Subject"
    
    # Test empty header
    result = verifier._decode_header("")
    assert result == ""
    
    # Test None
    result = verifier._decode_header(None)
    assert result == ""


@pytest.mark.asyncio
async def test_email_verifier_get_email_body():
    """Test extracting email body"""
    verifier = EmailVerifier(
        email_address="test@example.com",
        password="password"
    )
    
    # Create simple email
    from email.mime.text import MIMEText
    msg = MIMEText("This is the email body with code 123456")
    
    body = verifier._get_email_body(msg)
    assert "123456" in body
    assert "email body" in body


# Integration-like tests

@pytest.mark.asyncio
async def test_hotmail_pool_integration_workflow(temp_pool_file):
    """Test complete HotmailPool workflow"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    initial_stats = pool.get_stats()
    assert initial_stats['available'] > 0
    
    # Get email
    email, password = pool.get_next_email()
    assert '@' in email
    
    # Mark as used
    pool.mark_as_used(email)
    
    # Check stats updated
    new_stats = pool.get_stats()
    assert new_stats['used'] == initial_stats['used'] + 1
    assert new_stats['available'] == initial_stats['available'] - 1
    
    # Email should not be available anymore
    available_emails = [e[0] for e in pool.available_emails]
    assert email not in available_emails


@pytest.mark.asyncio  
async def test_email_pool_concurrent_access(temp_pool_file):
    """Test thread-safe pool access"""
    pool = HotmailPool(pool_file=temp_pool_file)
    
    # Get first email
    email1, _ = pool.get_next_email()
    
    # Get second email (if available)
    if len(pool) > 0:
        email2, _ = pool.get_next_email()
        
        # Should be different
        assert email1 != email2
