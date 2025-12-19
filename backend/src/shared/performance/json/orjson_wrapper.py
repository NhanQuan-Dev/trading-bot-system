"""
orjson wrapper - Fast JSON library

Usage:
    from shared.performance.json.orjson_wrapper import OrjsonSerializer
    
    data = OrjsonSerializer.dumps({"key": "value"})
    obj = OrjsonSerializer.loads(data)
"""

from typing import Any, Union

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    orjson = None


class OrjsonSerializer:
    """
    High-performance JSON serializer using orjson
    
    Features:
    - 2-3x faster than standard json
    - Supports datetime, UUID, dataclasses
    - Always returns bytes
    """
    
    @staticmethod
    def dumps(obj: Any, **kwargs) -> bytes:
        """
        Serialize to JSON bytes
        
        Args:
            obj: Object to serialize
            **kwargs: Additional options for orjson
            
        Returns:
            JSON as bytes
        """
        if not ORJSON_AVAILABLE:
            raise ImportError("orjson not installed. Run: pip install orjson")
        
        return orjson.dumps(obj, **kwargs)
    
    @staticmethod
    def dumps_str(obj: Any, **kwargs) -> str:
        """Serialize to JSON string (decoded)"""
        return OrjsonSerializer.dumps(obj, **kwargs).decode('utf-8')
    
    @staticmethod
    def loads(data: Union[str, bytes], **kwargs) -> Any:
        """
        Deserialize from JSON
        
        Args:
            data: JSON string or bytes
            **kwargs: Additional options
            
        Returns:
            Parsed object
        """
        if not ORJSON_AVAILABLE:
            raise ImportError("orjson not installed. Run: pip install orjson")
        
        return orjson.loads(data)


# Check availability
def is_available() -> bool:
    """Check if orjson is available"""
    return ORJSON_AVAILABLE
