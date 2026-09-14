import argparse
import asyncio

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.connection import Database
from app.learning.service import LearningService


async def main():
    configure_logging()
    parser = argparse.ArgumentParser(
        description="Actualizar datos históricos y entrenar modelos locales"
    )
    parser.add_argument("--train", action="store_true", help="Forzar entrenamiento tras actualizar")
    args = parser.parse_args()
    db = Database(Settings().duckdb_path)
    try:
        service = LearningService(db)
        await service.update(force_train=args.train)
        if service.job["errors"]:
            print(service.job["errors"])
            raise SystemExit(1)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
