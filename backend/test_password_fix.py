"""
Simple test script to verify password validation fix
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.security import validate_password_length, get_password_hash, verify_password


def test_password_validation():
    """Test password validation functionality"""
    print("Testing password validation fix...")
    print("=" * 60)

    # Test 1: Valid short password
    try:
        validate_password_length("short")
        print("✓ Test 1 PASSED: Short password validated successfully")
    except Exception as e:
        print(f"✗ Test 1 FAILED: {e}")
        return False

    # Test 2: Valid medium password
    try:
        validate_password_length("medium_password_123")
        print("✓ Test 2 PASSED: Medium password validated successfully")
    except Exception as e:
        print(f"✗ Test 2 FAILED: {e}")
        return False

    # Test 3: Password exactly 72 bytes (ASCII)
    try:
        validate_password_length("a" * 72)
        print("✓ Test 3 PASSED: 72-byte ASCII password validated successfully")
    except Exception as e:
        print(f"✗ Test 3 FAILED: {e}")
        return False

    # Test 4: Password exactly 72 bytes (Unicode emojis)
    try:
        validate_password_length("😀" * 18)
        print("✓ Test 4 PASSED: 72-byte Unicode password validated successfully")
    except Exception as e:
        print(f"✗ Test 4 FAILED: {e}")
        return False

    # Test 5: Password exceeding 72 bytes should be rejected
    try:
        validate_password_length("a" * 73)
        print("✗ Test 5 FAILED: 73-byte password should have been rejected")
        return False
    except ValueError as e:
        if "Password is too long" in str(e) and "73 bytes" in str(e):
            print("✓ Test 5 PASSED: 73-byte password correctly rejected")
        else:
            print(f"✗ Test 5 FAILED: Wrong error message: {e}")
            return False

    # Test 6: Unicode password exceeding 72 bytes should be rejected
    try:
        validate_password_length("😀" * 19)
        print("✗ Test 6 FAILED: 76-byte Unicode password should have been rejected")
        return False
    except ValueError as e:
        if "Password is too long" in str(e):
            print("✓ Test 6 PASSED: 76-byte Unicode password correctly rejected")
        else:
            print(f"✗ Test 6 FAILED: Wrong error message: {e}")
            return False

    # Test 7: Hash valid password
    try:
        password = "test_password_123"
        hashed = get_password_hash(password)
        if hashed.startswith("$2b$") and hashed != password:
            print("✓ Test 7 PASSED: Password hashed successfully")
        else:
            print("✗ Test 7 FAILED: Hash format incorrect")
            return False
    except Exception as e:
        print(f"✗ Test 7 FAILED: {e}")
        return False

    # Test 8: Hash password exceeding 72 bytes should fail
    try:
        get_password_hash("a" * 73)
        print("✗ Test 8 FAILED: Should not hash password exceeding 72 bytes")
        return False
    except ValueError as e:
        if "Password is too long" in str(e):
            print("✓ Test 8 PASSED: Correctly rejected password exceeding 72 bytes")
        else:
            print(f"✗ Test 8 FAILED: Wrong error message: {e}")
            return False

    # Test 9: Verify password
    try:
        password = "test_password_123"
        hashed = get_password_hash(password)
        if verify_password(password, hashed) and not verify_password("wrong", hashed):
            print("✓ Test 9 PASSED: Password verification works correctly")
        else:
            print("✗ Test 9 FAILED: Password verification incorrect")
            return False
    except Exception as e:
        print(f"✗ Test 9 FAILED: {e}")
        return False

    # Test 10: Unicode password hashing and verification
    try:
        password = "测试密码123😀"
        hashed = get_password_hash(password)
        if verify_password(password, hashed):
            print("✓ Test 10 PASSED: Unicode password hashing and verification works")
        else:
            print("✗ Test 10 FAILED: Unicode password verification failed")
            return False
    except Exception as e:
        print(f"✗ Test 10 FAILED: {e}")
        return False

    print("=" * 60)
    print("All tests PASSED! ✓")
    print("\nSummary:")
    print("- Password validation now rejects passwords exceeding 72 bytes")
    print("- Clear error messages are provided to users")
    print("- Passwords are no longer silently truncated")
    print("- Unicode passwords are properly handled")
    return True


if __name__ == "__main__":
    success = test_password_validation()
    sys.exit(0 if success else 1)
