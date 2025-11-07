"""Configuration management for the application"""

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


class Config:
    """Application configuration from environment variables"""

    # RapidAPI Configuration
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "")

    # IMAP Configuration
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.zmailservice.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration is present
        
        Returns:
            True if configuration is valid
        """
        if not cls.RAPIDAPI_KEY:
            raise ValueError("RAPIDAPI_KEY is required")
        return True


# Global config instance
config = Config()
