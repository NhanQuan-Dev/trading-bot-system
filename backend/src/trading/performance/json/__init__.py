"""
Fast JSON parsers/serializers

Wrapper cho các JSON library tối ưu như orjson, simdjson
"""

from typing import Any, Union
import json as stdlib_json

class JSONSerializer:
    """Abstract interface for JSON serialization"""
    
    @staticmethod
    def dumps(obj: Any) -> str:
        """Serialize object to JSON string"""
        raise NotImplementedError
    
    @staticmethod
    def loads(data: Union[str, bytes]) -> Any:
        """Deserialize JSON string to object"""
        raise NotImplementedError


class StandardJSONSerializer(JSONSerializer):
    """Standard library json (fallback)"""
    
    @staticmethod
    def dumps(obj: Any) -> str:
        return stdlib_json.dumps(obj)
    
    @staticmethod
    def loads(data: Union[str, bytes]) -> Any:
        return stdlib_json.loads(data)


# Default serializer (có thể override với orjson)
default_serializer = StandardJSONSerializer()
