import argparse
from datetime import date

from football_api.config import get_settings
from football_api.database import SessionLocal
from football_api.services.demo import seed_demo_data
from football_api.services.ingestion import IngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Operaciones de Football Analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest", help="Ejecuta la ingesta de una fecha")
    ingest.add_argument("--date", default=date.today().isoformat())
    seed = subparsers.add_parser("seed-demo", help="Carga datos de demostracion")
    seed.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    settings = get_settings()
    with SessionLocal() as db:
        target_date = date.fromisoformat(args.date)
        if args.command == "ingest":
            job = IngestionService(db, settings).run_daily(target_date)
            print(f"job={job.id} status={job.status} fixtures={job.fixtures_found}")
        else:
            fixtures = seed_demo_data(db, target_date, settings.timezone)
            print(f"fixtures_demo={len(fixtures)}")


if __name__ == "__main__":
    main()

