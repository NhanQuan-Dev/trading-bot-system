"""Unit tests for AssetBalance value object"""
import pytest
from decimal import Decimal

from src.trading.domain.portfolio.value_objects.asset_balance import AssetBalance


class TestAssetBalance:
    """Test suite for AssetBalance value object"""
    
    def test_create_balance_successfully(self):
        """Test: Can create balance with valid values"""
        balance = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        
        assert balance.asset == "USDT"
        assert balance.free == Decimal("1000")
        assert balance.locked == Decimal("200")
        assert balance.total == Decimal("1200")
    
    def test_asset_symbol_normalized_to_uppercase(self):
        """Test: Asset symbol is converted to uppercase"""
        balance = AssetBalance("usdt", Decimal("100"), Decimal("0"))
        
        assert balance.asset == "USDT"
    
    def test_reject_negative_free_balance(self):
        """Test: Raises error when free balance is negative"""
        with pytest.raises(ValueError, match="Free balance cannot be negative"):
            AssetBalance("USDT", Decimal("-100"), Decimal("0"))
    
    def test_reject_negative_locked_balance(self):
        """Test: Raises error when locked balance is negative"""
        with pytest.raises(ValueError, match="Locked balance cannot be negative"):
            AssetBalance("USDT", Decimal("100"), Decimal("-50"))
    
    def test_reject_empty_asset_symbol(self):
        """Test: Raises error when asset symbol is empty"""
        with pytest.raises(ValueError, match="Asset symbol cannot be empty"):
            AssetBalance("", Decimal("100"), Decimal("0"))
    
    def test_lock_amount_from_free_balance(self):
        """Test: Can lock amount from free balance"""
        balance = AssetBalance("USDT", Decimal("1000"), Decimal("0"))
        
        new_balance = balance.lock(Decimal("300"))
        
        assert new_balance.free == Decimal("700")
        assert new_balance.locked == Decimal("300")
        assert new_balance.total == Decimal("1000")
    
    def test_lock_fails_when_insufficient_free_balance(self):
        """Test: Cannot lock more than free balance"""
        balance = AssetBalance("USDT", Decimal("100"), Decimal("0"))
        
        with pytest.raises(ValueError, match="Cannot lock 200 USDT"):
            balance.lock(Decimal("200"))
    
    def test_unlock_amount_to_free_balance(self):
        """Test: Can unlock amount to free balance"""
        balance = AssetBalance("USDT", Decimal("700"), Decimal("300"))
        
        new_balance = balance.unlock(Decimal("100"))
        
        assert new_balance.free == Decimal("800")
        assert new_balance.locked == Decimal("200")
    
    def test_unlock_fails_when_insufficient_locked_balance(self):
        """Test: Cannot unlock more than locked balance"""
        balance = AssetBalance("USDT", Decimal("700"), Decimal("100"))
        
        with pytest.raises(ValueError, match="Cannot unlock 200 USDT"):
            balance.unlock(Decimal("200"))
    
    def test_add_amount_to_free_balance(self):
        """Test: Can add amount to free balance"""
        balance = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        
        new_balance = balance.add(Decimal("500"))
        
        assert new_balance.free == Decimal("1500")
        assert new_balance.locked == Decimal("200")
    
    def test_subtract_amount_from_free_balance(self):
        """Test: Can subtract amount from free balance"""
        balance = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        
        new_balance = balance.add(Decimal("-300"))
        
        assert new_balance.free == Decimal("700")
        assert new_balance.locked == Decimal("200")
    
    def test_add_fails_when_result_negative(self):
        """Test: Cannot add amount that results in negative balance"""
        balance = AssetBalance("USDT", Decimal("100"), Decimal("0"))
        
        with pytest.raises(ValueError, match="Resulting free balance cannot be negative"):
            balance.add(Decimal("-200"))
    
    def test_value_equality(self):
        """Test: Two balances with same values are equal"""
        balance1 = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        balance2 = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        
        assert balance1 == balance2
        assert hash(balance1) == hash(balance2)
    
    def test_value_inequality_different_free(self):
        """Test: Balances with different free amounts are not equal"""
        balance1 = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        balance2 = AssetBalance("USDT", Decimal("900"), Decimal("200"))
        
        assert balance1 != balance2
    
    def test_value_inequality_different_asset(self):
        """Test: Balances with different assets are not equal"""
        balance1 = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        balance2 = AssetBalance("BTC", Decimal("1000"), Decimal("200"))
        
        assert balance1 != balance2
    
    def test_immutability(self):
        """Test: Operations return new instances (immutable)"""
        balance = AssetBalance("USDT", Decimal("1000"), Decimal("200"))
        
        new_balance = balance.lock(Decimal("100"))
        
        # Original unchanged
        assert balance.free == Decimal("1000")
        assert balance.locked == Decimal("200")
        
        # New instance has changes
        assert new_balance.free == Decimal("900")
        assert new_balance.locked == Decimal("300")
