from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Any, Dict

@dataclass
class LayerConfig:
    enabled: bool = True

class LayerBase(ABC):
    def __init__(self, config: LayerConfig):
        self.config = config
        self._is_active = False

    @property
    def is_enabled(self) -> bool:
        return self.config.enabled

    @property
    def is_active(self) -> bool:
        return self._is_active

    @abstractmethod
    def activate(self) -> bool:
        pass

    @abstractmethod
    def deactivate(self) -> bool:
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def check_status(self) -> Dict[str, Any]:
        pass
