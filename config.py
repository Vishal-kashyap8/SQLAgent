# Configuration settings for SQL Server DBA Agent
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Default model: gemini-3.5-flash (fast, highly reliable, free-tier supported)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# SQL Server Configuration
# Using localhost by default, with Windows Authentication
SQL_SERVER = os.getenv("SQL_SERVER", "localhost")
SQL_DATABASE = os.getenv("SQL_DATABASE", "master")
SQL_DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 17 for SQL Server")

# Set to True to use Windows Authentication (Trusted_Connection)
SQL_TRUSTED_CONNECTION = os.getenv("SQL_TRUSTED_CONNECTION", "yes").lower() in ("yes", "true", "1")

# Optional SQL authentication (if SQL_TRUSTED_CONNECTION is false)
SQL_USERNAME = os.getenv("SQL_USERNAME", "")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

