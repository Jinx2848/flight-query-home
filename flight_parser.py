import argparse
from datetime import datetime
import json
import logging
import os
import sys

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

STUDENT_ID = "260ADB145"
FIRST_NAME = "durumelek"
LAST_NAME = "dogru"


def _setup_logger(log_path: str) -> tuple[logging.Logger, logging.FileHandler]:
    logger = logging.getLogger("flight_parser")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger, handler


def _teardown_logger(logger: logging.Logger, handler: logging.FileHandler) -> None:
    logger.removeHandler(handler)
    handler.close()


def _valid_db_shape(data: object) -> bool:
    if not isinstance(data, list):
        return False
    expected_keys = {
        "flight_id",
        "origin",
        "destination",
        "departure_datetime",
        "arrival_datetime",
        "price",
    }
    return all(isinstance(row, dict) and set(row.keys()) == expected_keys for row in data)


def main(argv: list[str] | None = None) -> int:
    raw_args = sys.argv[1:] if argv is None else argv

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-i", dest="input_file", default=None)
    parser.add_argument("-d", dest="input_dir", default=None)
    parser.add_argument("-j", dest="json_db", default=None)
    parser.add_argument("-a", dest="airports_file", default=None)
    parser.add_argument("-o", dest="output_db", default=None)
    parser.add_argument("-q", dest="queries_file", default=None)
    parser.add_argument("-r", dest="response_dir", default=".")

    try:
        args = parser.parse_args(raw_args)
    except SystemExit as exc:
        if exc.code == 0 or exc.code is None:
            return 0
        return 2

    sources = [s for s in (args.input_file, args.input_dir, args.json_db) if s is not None]
    if len(sources) != 1:
        print("Error: Exactly one of -i, -d, or -j is required.", file=sys.stderr)
        return 2

    csv_mode = args.input_file is not None or args.input_dir is not None

    if csv_mode and not args.airports_file:
        print("Error: -a is required with -i or -d.", file=sys.stderr)
        return 2

    if not csv_mode and args.output_db is not None:
        print("Error: -o cannot be used with -j.", file=sys.stderr)
        return 2

    records: list[dict] = []

    if csv_mode:
        if not os.path.isfile(args.airports_file):
            print(f"Error: Airport file not found: {args.airports_file}", file=sys.stderr)
            return 1

        if args.input_file is not None:
            if not os.path.isfile(args.input_file):
                print(f"Error: Input CSV file not found: {args.input_file}", file=sys.stderr)
                return 1
            csv_files = [args.input_file]
        else:
            if not os.path.isdir(args.input_dir):
                print(f"Error: Input directory not found: {args.input_dir}", file=sys.stderr)
                return 1
            try:
                names = os.listdir(args.input_dir)
            except OSError as exc:
                print(f"Error: Cannot read folder {args.input_dir}: {exc}", file=sys.stderr)
                return 1
            csv_files = sorted(
                os.path.join(args.input_dir, name)
                for name in names
                if name.endswith(".csv") and os.path.isfile(os.path.join(args.input_dir, name))
            )
            if not csv_files:
                print(f"Error: No .csv files found in {args.input_dir}", file=sys.stderr)
                return 1

        out_path = args.output_db if args.output_db is not None else "db.json"
        out_dir = os.path.dirname(os.path.abspath(out_path))
        log_path = os.path.join(out_dir, "errors.log")

        logger, handler = _setup_logger(log_path)
        try:
            airports = load_airports(args.airports_file)
            records, error_lines = parse_files(csv_files, airports)
            for line in error_lines:
                logger.warning(line)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        finally:
            _teardown_logger(logger, handler)
    else:
        if not os.path.isfile(args.json_db):
            print(f"Error: JSON database not found: {args.json_db}", file=sys.stderr)
            return 1
        try:
            with open(args.json_db, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"Error: Invalid JSON database: {exc}", file=sys.stderr)
            return 1
        if not _valid_db_shape(loaded):
            print("Error: JSON database has invalid shape.", file=sys.stderr)
            return 1
        records = loaded

    if args.queries_file is not None:
        if not os.path.isfile(args.queries_file):
            print(f"Error: Queries file not found: {args.queries_file}", file=sys.stderr)
            return 1
        if not os.path.isdir(args.response_dir):
            print(f"Error: Response folder not found: {args.response_dir}", file=sys.stderr)
            return 1

        try:
            with open(args.queries_file, "r", encoding="utf-8") as f:
                queries = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print(f"Error: Invalid queries JSON: {exc}", file=sys.stderr)
            return 1

        if not isinstance(queries, (dict, list)):
            print("Error: Queries JSON must be an object or array.", file=sys.stderr)
            return 1

        results = run_queries(records, queries)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{stamp}.json"
        response_path = os.path.join(args.response_dir, filename)

        try:
            with open(response_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        except OSError as exc:
            print(f"Error: Cannot write response file: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
