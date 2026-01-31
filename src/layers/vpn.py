from dataclasses import dataclass
from typing import Optional
from .base import LayerConfig

@dataclass
class VPNConfig(LayerConfig):
    provider: str = "protonvpn"
    country: str = "US"
    city: Optional[str] = None
    server: Optional[str] = None
    protocol: str = "wireguard"
