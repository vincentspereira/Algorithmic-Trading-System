import logging
import logging.config
import os
from pythonjsonlogger.json import JsonFormatter


def setup_logging():
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.json.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "handlers": ["console"],
            "level": log_level,
        },
    }

    logging.config.dictConfig(config)