
from queueflow_device_manager.config import Config

def test_env_openai_config():
    config = Config(_env_file="./tests/.env.openai") # type: ignore

    assert config.API_KEY == "sk_test_1234567890abcdef1234567890abcdef"
    assert config.MODEL == "openai/gpt-4o"

def test_env_ollama_config():
    config = Config(_env_file="./tests/.env.ollama") # type: ignore

    assert config.API_KEY == ""
    assert config.MODEL == "ollama_chat/qwen3:8b"

def test_default_config():
    config = Config()

    assert config.API_KEY == ""
    assert config.MODEL == "ollama_chat/qwen3:8b"