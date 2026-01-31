from dataclasses import dataclass
from typing import Optional
from .base import LayerConfig

@dataclass
class ProxyConfig(LayerConfig):
    protocol: str = "http"
    host: str = "localhost"
    port: int = 8080
    username: Optional[str] = None
    password: Optional[str] = None
