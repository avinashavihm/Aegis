"""Base capability class for agent capabilities"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseCapability(ABC):
    """Base class for agent capabilities"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute the capability"""
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        pass
    
    def get_capability_type(self) -> str:
        """Get the capability type"""
        return self.__class__.__name__

