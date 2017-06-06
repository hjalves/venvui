# -*- coding: utf-8 -*-

# http_host = "127.0.0.1"
# http_port = 8000
# temp_path = "./tmp"
# venv_path = "./venvs"


# Logging config
logging = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s.%(msecs)d - %(name)s - %(levelname)s - %(message)s"
        },
        "colored": {
            "()": "colorlog.ColoredFormatter",
            "format": "%(asctime)s.%(msecs)03d %(bold)s%(log_color)s[%(levelname)4.4s]%(reset)s (%(threadName)s) %(name)s: %(message_log_color)s%(message)s",
            "datefmt": "%b %d %H:%M:%S",
            "log_colors": {
                "DEBUG":    "cyan",
                "INFO":     "green",
                "WARNING":  "yellow",
                "ERROR":    "red",
                "CRITICAL": "red,bg_white"
            },
            "secondary_log_colors": {
                "message": {
                        "DEBUG":    "bold",
                        "INFO":     "bold",
                        "WARNING":  "bold_yellow",
                        "ERROR":    "bold_red",
                        "CRITICAL": "bold_red"
                }
            }
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "colored",
            "stream": "ext://sys.stdout"
        },
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"]
    },
    "loggers": {
        "asyncio": {
            "level": "DEBUG"
        },
        "venvui": {
            "level": "DEBUG"
        }
    }
}
