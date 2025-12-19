"""
simdjson wrapper - Ultra-fast JSON parser

Usage:
    from shared.performance.json.simdjson_wrapper import SimdJSONSerializer
    
    obj = SimdJSONSerializer.loads(json_data)
"""

from typing import Any, Union

try:
    import simdjson
    SIMDJSON_AVAILABLE = True
except ImportError:
    SIMDJSON_AVAILABLE = False
    simdjson = None


class SimdJSONSerializer:
    """
    Ultra-fast JSON parser using simdjson
    
    Features:
    - Up to 4x faster parsing than standard json
    - Only for parsing (not serialization)
    - Best for large JSON documents
    """
    
    def __init__(self):
        if not SIMDJSON_AVAILABLE:
            raise ImportError("simdjson not installed. Run: pip install pysimdjson")
        self.parser = simdjson.Parser()
    
    def loads(self, data: Union[str, bytes]) -> Any:
        """
        Parse JSON using simdjson
        
        Args:
            data: JSON string or bytes
            
        Returns:
            Parsed object
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return self.parser.parse(data)


# Singleton instance
_parser_instance = None


def get_parser() -> SimdJSONSerializer:
    """Get singleton parser instance"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = SimdJSONSerializer()
    return _parser_instance


def is_available() -> bool:
    """Check if simdjson is available"""
    return SIMDJSON_AVAILABLE
