import json
import logging
import sys
from datetime import datetime, timezone


def setup_logging(level: str = 'INFO') -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    root.addHandler(handler)


def log_json(logger: logging.Logger, level: int, event: str, **payload) -> None:
    message = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'event': event,
        **payload,
    }
    logger.log(level, json.dumps(message, ensure_ascii=True, default=str))
