import os
import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ABB AC450 Migration Studio"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Use system temp on Render/ephemeral hosts (/tmp); survives process quirks only.
    SYS_TEMP: Path = Path(tempfile.gettempdir())
    UPLOAD_DIR: Path = SYS_TEMP / "abb_ac450" / "uploads"
    OUTPUT_DIR: Path = SYS_TEMP / "abb_ac450" / "outputs"
    LOG_DIR: Path = SYS_TEMP / "abb_ac450" / "logs"

    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".xlsx", ".xlsm", ".xls"}

    # Production knobs (also set via Render env vars)
    PC_LIGHT_PDF_READ: str = os.getenv("PC_LIGHT_PDF_READ", "1")
    DB_LIGHT_PDF_READ: str = os.getenv("DB_LIGHT_PDF_READ", "1")
    ENABLE_PC_OCR: str = os.getenv("ENABLE_PC_OCR", "0")

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()

# Ensure required directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
