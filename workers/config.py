"""Configuration management for the application"""

import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any

load_dotenv()


class Config:
    """Application configuration fetched from backend API"""

    # Backend API Configuration
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8080")
    
    # Redis Configuration (still from env)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # Settings fetched from backend
    RAPIDAPI_KEY: str = ""
    IMAP_SERVER: str = ""
    IMAP_PORT: int = 993
    IMAP_USERNAME: str = ""
    IMAP_PASSWORD: str = ""
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    PROXY_URL: str = ""
    WORKER_COUNT: int = 1
    RETRY_COUNT: int = 3
    TIMEOUT: int = 30

    _settings_loaded: bool = False

    @classmethod
    def fetch_from_backend(cls, timeout: int = 5) -> Dict[str, Any]:
        """
        Fetch configuration from backend API
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Dict containing settings from backend
            
        Raises:
            requests.RequestException: If backend is unreachable
        """
        try:
            response = requests.get(
                f"{cls.BACKEND_URL}/api/settings",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to fetch settings from backend: {e}")
            raise

    @classmethod
    def load_settings(cls) -> None:
        """
        Load settings from backend API and populate class variables
        """
        if cls._settings_loaded:
            return

        try:
            response_data = cls.fetch_from_backend()
            
            # Extract settings from the data field
            settings = response_data.get("data", {})
            
            # Update class variables with backend settings
            cls.RAPIDAPI_KEY = settings.get("rapidapi_key", "")
            cls.IMAP_SERVER = settings.get("imap_server", "")
            cls.IMAP_PORT = settings.get("imap_port", 993)
            cls.IMAP_USERNAME = settings.get("imap_username", "")
            cls.IMAP_PASSWORD = settings.get("imap_password", "")
            cls.SMTP_SERVER = settings.get("smtp_server", "")
            cls.SMTP_PORT = settings.get("smtp_port", 587)
            cls.SMTP_USERNAME = settings.get("smtp_username", "")
            cls.SMTP_PASSWORD = settings.get("smtp_password", "")
            cls.PROXY_URL = settings.get("proxy_url", "")
            cls.WORKER_COUNT = settings.get("worker_count", 1)
            cls.RETRY_COUNT = settings.get("retry_count", 3)
            cls.TIMEOUT = settings.get("timeout", 30)
            
            cls._settings_loaded = True
            print("Settings loaded successfully from backend")
            
        except Exception as e:
            print(f"Error loading settings from backend: {e}")
            print("Using default/empty values")

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration is present
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If required settings are missing
        """
        if not cls._settings_loaded:
            cls.load_settings()
            
        if not cls.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY is required - please configure in dashboard settings")
        return True


# Global config instance
config = Config()

# Auto-load settings on import
try:
    config.load_settings()
except Exception as e:
    print(f"Warning: Could not load settings from backend on import: {e}")
