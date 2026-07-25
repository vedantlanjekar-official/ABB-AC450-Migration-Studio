import logging
from pathlib import Path
from typing import Optional
from backend.core.config import settings

def get_logger(job_id: Optional[str] = None) -> logging.Logger:
    logger_name = f"ac450_{job_id}" if job_id else "ac450_global"
    logger = logging.getLogger(logger_name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Console handler
        c_handler = logging.StreamHandler()
        c_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        c_handler.setFormatter(formatter)
        logger.addHandler(c_handler)
        
        # Job specific file handler if job_id provided
        if job_id:
            log_file = settings.LOG_DIR / f"{job_id}.log"
            f_handler = logging.FileHandler(log_file, encoding='utf-8')
            f_handler.setLevel(logging.INFO)
            f_handler.setFormatter(formatter)
            logger.addHandler(f_handler)
            
    return logger
