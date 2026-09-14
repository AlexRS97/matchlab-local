import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                **{
                    key: getattr(record, key, None)
                    for key in (
                        "provider",
                        "endpoint",
                        "fixture",
                        "duration",
                        "status",
                        "cache_hit",
                        "error",
                        "phase",
                    )
                },
            },
            ensure_ascii=False,
        )


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("matchlab")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    # HTTP loggers may include request URLs. Only sanitized provider events are logged.
    logging.getLogger("httpx").setLevel(logging.WARNING)
