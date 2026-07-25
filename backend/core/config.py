import os
import tempfile
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ABB AC450 DB Element Converter"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    
    # In serverless environments (e.g. Vercel), use system temp directory (/tmp)
    SYS_TEMP: Path = Path(tempfile.gettempdir())
    UPLOAD_DIR: Path = SYS_TEMP / "abb_ac450" / "uploads"
    OUTPUT_DIR: Path = SYS_TEMP / "abb_ac450" / "outputs"
    LOG_DIR: Path = SYS_TEMP / "abb_ac450" / "logs"
    
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}
    
    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()

# Ensure required directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
