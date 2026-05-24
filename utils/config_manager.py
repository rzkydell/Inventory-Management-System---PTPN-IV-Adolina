import os
import json
from utils.path_helper import get_root_dir

CONFIG_FILE = os.path.join(get_root_dir(), "config.json")

def load_config():
    """Load configuration from config.json, returning default values if not exists."""
    if not os.path.exists(CONFIG_FILE):
        return {"ip_camera_url": ""}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"ip_camera_url": ""}

def save_config(config_data):
    """Save configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_ip_camera_url():
    """Get the current IP Camera URL from config."""
    config = load_config()
    return config.get("ip_camera_url", "").strip()

def set_ip_camera_url(url):
    """Set the IP Camera URL in config."""
    config = load_config()
    config["ip_camera_url"] = url.strip()
    return save_config(config)

def get_gemini_api_key():
    """Get the current Gemini API Key from config, fallback to environment variable or leaked key if needed."""
    # 1. Coba dari environment variable dulu
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
        
    # 2. Coba dari config.json
    config = load_config()
    stored_key = config.get("gemini_api_key", "").strip()
    if stored_key:
        return stored_key
        
    # 3. Fallback ke default key lama (jika belum disetting)
    return "AIzaSyA2srzqjMy2wLTliBTjd--Mc6-eb2eULXs"

def set_gemini_api_key(key):
    """Set the Gemini API Key in config."""
    config = load_config()
    config["gemini_api_key"] = key.strip()
    return save_config(config)
