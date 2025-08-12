import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_OLLAMA="ollama_chat/qwen3:8b"

class Config(BaseSettings):
    """Configuration settings for the queueflow device manager."""

    model_config = SettingsConfigDict(
        env_file="../.env",
        case_sensitive=True,
    )
    name: str = "queueflow_device_manager"
    API_KEY: str = Field(default="")
    MODEL: str = Field(default=MODEL_OLLAMA)

config = Config()
