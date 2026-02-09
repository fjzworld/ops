"""
Test security functions, specifically password validation
"""
import pytest
from app.core.security import validate_password_length, get_password_hash, verify_password


def test_validate_password_length_valid():
    """Test that valid passwords pass validation"""
    # Short password
    validate_password_length("short")

    # Medium password
    validate_password_length("medium_password_123")

    # Long but within limit (72 bytes)
    # ASCII characters: 1 char = 1 byte
    validate_password_length("a" * 72)

    # Unicode characters (multi-byte)
    # Each emoji is 4 bytes, so 18 emojis = 72 bytes
    validate_password_length("😀" * 18)


def test_validate_password_length_invalid():
    """Test that passwords exceeding 72 bytes are rejected"""
    # ASCII password exceeding 72 bytes
    with pytest.raises(ValueError) as exc_info:
        validate_password_length("a" * 73)
    assert "Password is too long" in str(exc_info.value)
    assert "73 bytes" in str(exc_info.value)
    assert "Maximum allowed length is 72 bytes" in str(exc_info.value)

    # Unicode password exceeding 72 bytes
    # 19 emojis = 76 bytes
    with pytest.raises(ValueError) as exc_info:
        validate_password_length("😀" * 19)
    assert "Password is too long" in str(exc_info.value)


def test_get_password_hash_valid():
    """Test that valid passwords can be hashed"""
    password = "test_password_123"
    hashed = get_password_hash(password)

    # Hash should be a string
    assert isinstance(hashed, str)

    # Hash should not be the same as the password
    assert hashed != password

    # Hash should start with bcrypt prefix
    assert hashed.startswith("$2b$")


def test_get_password_hash_invalid():
    """Test that invalid passwords cannot be hashed"""
    # Password exceeding 72 bytes should raise ValueError
    with pytest.raises(ValueError):
        get_password_hash("a" * 73)


def test_verify_password():
    """Test password verification"""
    password = "test_password_123"
    hashed = get_password_hash(password)

    # Correct password should verify
    assert verify_password(password, hashed) is True

    # Incorrect password should not verify
    assert verify_password("wrong_password", hashed) is False


def test_password_with_unicode():
    """Test passwords with Unicode characters"""
    # Password with emoji
    password = "test😀password"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True

    # Password with Chinese characters
    password = "测试密码123"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True


def test_password_exactly_72_bytes():
    """Test password that is exactly 72 bytes"""
    # ASCII: 72 characters
    password = "a" * 72
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True

    # Unicode: 18 emojis (4 bytes each = 72 bytes)
    password = "😀" * 18
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True


def test_password_just_over_72_bytes():
    """Test password that is just over 72 bytes"""
    # ASCII: 73 characters
    with pytest.raises(ValueError):
        get_password_hash("a" * 73)

    # Unicode: 19 emojis (76 bytes)
    with pytest.raises(ValueError):
        get_password_hash("😀" * 19)
