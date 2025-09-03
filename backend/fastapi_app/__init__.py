"""
FastAPI应用包初始化
"""

from .main import app
from .config import settings

__version__ = "2.0.0"
__all__ = ["app", "settings"]