"""Unit tests for User domain value objects."""

import pytest
from src.trading.domain.user import Email, HashedPassword


class TestEmail:
    """Test Email value object."""
    
    def test_valid_email_creation(self):
        """Test creating email with valid format."""
        email = Email("user@example.com")
        assert email.value == "user@example.com"
    
    def test_valid_email_formats(self):
        """Test various valid email formats."""
        valid_emails = [
            "simple@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_123@test-domain.com",
        ]
        
        for email_str in valid_emails:
            email = Email(email_str)
            assert email.value == email_str
    
    def test_invalid_email_formats(self):
        """Test that invalid email formats raise ValueError."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "user@.com",
            "",
        ]
        
        for email_str in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                Email(email_str)
    
    def test_email_equality(self):
        """Test email equality comparison."""
        email1 = Email("user@example.com")
        email2 = Email("user@example.com")
        email3 = Email("other@example.com")
        
        assert email1 == email2
        assert email1 != email3
    
    def test_email_immutable(self):
        """Test that email is immutable."""
        email = Email("user@example.com")
        
        with pytest.raises(AttributeError):
            email.value = "other@example.com"
    
    def test_email_string_representation(self):
        """Test email string representation."""
        email = Email("user@example.com")
        assert str(email) == "user@example.com"


class TestHashedPassword:
    """Test HashedPassword value object."""
    
    def test_create_from_plain_password(self):
        """Test creating hashed password from plain text."""
        plain_password = "SecurePass123"
        hashed = HashedPassword.from_plain(plain_password)
        
        assert hashed.value is not None
        assert len(hashed.value) > 50  # bcrypt hash length
        assert hashed.value != plain_password  # Should not store plain text
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        plain_password = "SecurePass123"
        hashed = HashedPassword.from_plain(plain_password)
        
        assert hashed.verify(plain_password) is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        plain_password = "SecurePass123"
        hashed = HashedPassword.from_plain(plain_password)
        
        assert hashed.verify("WrongPassword") is False
        assert hashed.verify("") is False
        assert hashed.verify("secure123") is False
    
    def test_password_not_stored_as_plain_text(self):
        """Test that password is never stored as plain text."""
        plain_password = "SecurePass123"
        hashed = HashedPassword.from_plain(plain_password)
        
        # Hash should not contain plain password
        assert plain_password not in hashed.value
        # Hash should start with bcrypt prefix
        assert hashed.value.startswith("$2b$")
    
    def test_different_passwords_have_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "Password1"
        password2 = "Password2"
        
        hash1 = HashedPassword.from_plain(password1)
        hash2 = HashedPassword.from_plain(password2)
        
        assert hash1.value != hash2.value
    
    def test_same_password_different_salt(self):
        """Test that same password produces different hashes (due to salt)."""
        plain_password = "SecurePass123"
        
        hash1 = HashedPassword.from_plain(plain_password)
        hash2 = HashedPassword.from_plain(plain_password)
        
        # Different hashes due to salt
        assert hash1.value != hash2.value
        # But both verify correctly
        assert hash1.verify(plain_password) is True
        assert hash2.verify(plain_password) is True
    
    def test_hashed_password_immutable(self):
        """Test that hashed password is immutable."""
        hashed = HashedPassword.from_plain("SecurePass123")
        
        with pytest.raises(AttributeError):
            hashed.value = "newhash"
    
    def test_create_from_existing_hash(self):
        """Test creating HashedPassword from existing hash."""
        # Create initial hash
        plain_password = "SecurePass123"
        hash1 = HashedPassword.from_plain(plain_password)
        
        # Create new instance from existing hash
        hash2 = HashedPassword(hash1.value)
        
        # Should be able to verify with existing hash
        assert hash2.verify(plain_password) is True
    
    def test_empty_password_fails(self):
        """Test that empty password fails verification."""
        hashed = HashedPassword.from_plain("SecurePass123")
        assert hashed.verify("") is False
    
    def test_password_with_special_characters(self):
        """Test password with special characters."""
        special_password = "P@ssw0rd!#$%^&*()"
        hashed = HashedPassword.from_plain(special_password)
        
        assert hashed.verify(special_password) is True
        assert hashed.verify("P@ssw0rd") is False
