import logging
import sys
import structlog
from app.core.config import settings

import re

SENSITIVE_KEYS = {
    "authorization",
    "bearer",
    "token",
    "id_token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "gemini_api_key",
    "google_maps_api_key",
    "weatherapi_api_key",
    "traffic_api_key",
    "llm_api_key",
    "secret",
    "password",
    "cookie",
    "session",
}

TOKEN_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE)
API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z\-_]{35}", re.IGNORECASE)


def redact_sensitive_value(key: str, value):
    if any(s in str(key).lower() for s in SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, str):
        val = TOKEN_PATTERN.sub(r"\1[REDACTED]", value)
        val = API_KEY_PATTERN.sub(r"[REDACTED]", val)
        return val
    elif isinstance(value, dict):
        return {k: redact_sensitive_value(k, v) for k, v in value.items()}
    elif isinstance(value, list):
        return [redact_sensitive_value(key, v) for v in value]
    return value


def redact_sensitive_processor(logger, method_name, event_dict):
    return {k: redact_sensitive_value(k, v) for k, v in event_dict.items()}


def setup_logging():
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redact_sensitive_processor,
            structlog.processors.JSONRenderer() if settings.environment != "development" else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    logger = structlog.get_logger("weathergpt")
    logger.info("Logging configured", level=settings.log_level, env=settings.environment)

def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
