"""Order validation service for exchange constraints."""
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Symbol trading constraints from exchange."""
    min_quantity: Decimal
    max_quantity: Decimal
    quantity_precision: int
    price_precision: int
    min_notional: Decimal  # Minimum order value (price * quantity)


class OrderValidator:
    """
    Service for validating orders against exchange symbol constraints.
    
    Caches symbol info to avoid repeated API calls.
    """
    
    def __init__(self):
        self._symbol_cache: Dict[str, SymbolInfo] = {}
    
    async def get_symbol_info(self, exchange_client, symbol: str) -> SymbolInfo:
        """
        Get symbol trading constraints from exchange.
        
        Caches results to avoid repeated API calls.
        """
        # Check cache first
        cache_key = f"{exchange_client.__class__.__name__}_{symbol}"
        if cache_key in self._symbol_cache:
            return self._symbol_cache[cache_key]
        
        try:
            # Fetch from exchange
            exchange_info = await exchange_client.get_exchange_info()
            
            # Find symbol info
            symbol_data = next(
                (s for s in exchange_info.get('symbols', []) if s['symbol'] == symbol),
                None
            )
            
            if not symbol_data:
                # Default constraints if symbol not found
                logger.warning(f"Symbol {symbol} not found in exchange info, using defaults")
                return self._get_default_symbol_info()
            
            # Parse filters
            filters = {f['filterType']: f for f in symbol_data.get('filters', [])}
            
            # Extract constraints
            lot_size = filters.get('LOT_SIZE', {})
            price_filter = filters.get('PRICE_FILTER', {})
            min_notional_filter = filters.get('MIN_NOTIONAL', {})
            
            symbol_info = SymbolInfo(
                min_quantity=Decimal(lot_size.get('minQty', '0.001')),
                max_quantity=Decimal(lot_size.get('maxQty', '9000')),
                quantity_precision=symbol_data.get('quantityPrecision', 8),
                price_precision=symbol_data.get('pricePrecision', 2),
                min_notional=Decimal(min_notional_filter.get('minNotional', '5')),
            )
            
            # Cache it
            self._symbol_cache[cache_key] = symbol_info
            logger.info(f"Cached symbol info for {symbol}: min_qty={symbol_info.min_quantity}, "
                       f"price_precision={symbol_info.price_precision}")
            
            return symbol_info
            
        except Exception as e:
            logger.error(f"Failed to fetch symbol info for {symbol}: {e}")
            return self._get_default_symbol_info()
    
    def _get_default_symbol_info(self) -> SymbolInfo:
        """Return sensible defaults when symbol info unavailable."""
        return SymbolInfo(
            min_quantity=Decimal('0.001'),
            max_quantity=Decimal('9000'),
            quantity_precision=8,
            price_precision=2,
            min_notional=Decimal('5'),
        )
    
    def validate_and_adjust_quantity(
        self, 
        quantity: Decimal, 
        symbol_info: SymbolInfo
    ) -> Decimal:
        """
        Validate and adjust quantity to meet exchange constraints.
        
        Raises:
            ValueError: If quantity is below minimum after adjustment
        """
        # Round to correct precision
        precision = Decimal('0.1') ** symbol_info.quantity_precision
        adjusted_qty = quantity.quantize(precision, rounding=ROUND_DOWN)
        
        # Check minimum
        if adjusted_qty < symbol_info.min_quantity:
            raise ValueError(
                f"Quantity {quantity} (adjusted: {adjusted_qty}) is below minimum {symbol_info.min_quantity}"
            )
        
        # Check maximum
        if adjusted_qty > symbol_info.max_quantity:
            raise ValueError(
                f"Quantity {quantity} exceeds maximum {symbol_info.max_quantity}"
            )
        
        return adjusted_qty
    
    def validate_and_adjust_price(
        self, 
        price: Optional[Decimal], 
        symbol_info: SymbolInfo
    ) -> Optional[Decimal]:
        """
        Validate and adjust price to meet exchange precision.
        
        Returns None if price is None (e.g., for market orders).
        """
        if price is None:
            return None
        
        # Round to correct precision
        precision = Decimal('0.1') ** symbol_info.price_precision
        adjusted_price = price.quantize(precision, rounding=ROUND_DOWN)
        
        if adjusted_price <= 0:
            raise ValueError(f"Price {price} must be positive")
        
        return adjusted_price
    
    def validate_notional(
        self, 
        quantity: Decimal, 
        price: Optional[Decimal], 
        symbol_info: SymbolInfo
    ) -> None:
        """
        Validate that order value (price * quantity) meets minimum.
        
        Only applies to limit orders where price is known.
        """
        if price is None:
            # Skip for market orders
            return
        
        notional = quantity * price
        if notional < symbol_info.min_notional:
            raise ValueError(
                f"Order value {notional} (qty: {quantity}, price: {price}) "
                f"is below minimum {symbol_info.min_notional}"
            )
    
    async def validate_order_constraints(
        self,
        exchange_client,
        symbol: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """
        Validate and adjust order parameters to meet exchange constraints.
        
        Returns:
            Dict with adjusted parameters: quantity, price, stop_price
            
        Raises:
            ValueError: If constraints cannot be met
        """
        # Get symbol info
        symbol_info = await self.get_symbol_info(exchange_client, symbol)
        
        # Validate and adjust parameters
        adjusted_quantity = self.validate_and_adjust_quantity(quantity, symbol_info)
        adjusted_price = self.validate_and_adjust_price(price, symbol_info)
        adjusted_stop_price = self.validate_and_adjust_price(stop_price, symbol_info)
        
        # Validate notional value
        self.validate_notional(adjusted_quantity, adjusted_price, symbol_info)
        
        return {
            'quantity': adjusted_quantity,
            'price': adjusted_price,
            'stop_price': adjusted_stop_price,
        }
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear symbol info cache."""
        if symbol:
            # Clear specific symbol
            self._symbol_cache = {
                k: v for k, v in self._symbol_cache.items() 
                if not k.endswith(f"_{symbol}")
            }
        else:
            # Clear all
            self._symbol_cache.clear()
