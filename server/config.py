"""Configuration models and YAML loader for KindlePad."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8070
    token: str = ""


class ScreenConfig(BaseModel):
    width: int = 1024
    height: int = 758


class DeviceConfig(BaseModel):
    id: str
    name: str
    type: str = "light"
    room: str = ""


class DirigeraConfig(BaseModel):
    hub_ip: str = ""
    token: str = ""
    devices: list[DeviceConfig] = []


class LineConfig(BaseModel):
    id: str
    display_name: str


class StationConfig(BaseModel):
    naptan_id: str
    display_name: str


class TflConfig(BaseModel):
    lines: list[LineConfig] = []
    stations: list[StationConfig] = []
    refresh_interval_seconds: int = 120


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    screen: ScreenConfig = ScreenConfig()
    dirigera: DirigeraConfig = DirigeraConfig()
    tfl: TflConfig = TflConfig()


def load_config(path: str) -> AppConfig:
    """Load application configuration from a YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()
    with open(config_path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return AppConfig()
    # Support both pydantic v1 and v2
    if hasattr(AppConfig, "model_validate"):
        return AppConfig.model_validate(data)
    return AppConfig.parse_obj(data)
