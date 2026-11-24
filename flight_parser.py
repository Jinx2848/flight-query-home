"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import sys
import argparse
from datetime import datetime
import json
import os
import logging
from csv_loader import parse_files
from query import run_queries
from validator import load_airports

# TODO: fill in your details: plain ASCII, no spaces or underscores.
STUDENT_ID = "260ADB145"
FIRST_NAME = "DuruMelek"
LAST_NAME = "Dogru"

class ArgumentParserError(Exception):
    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message:str) -> None:
        raise ArgumentParserError(message, code = 2)

def build_parser() -> StrictArgumentParser:
    parser = StrictArgumentParser(add_help=True)
    parser.add_argument("-i", dest="imput_file", default=None)
    parser.add_argument("-d", dest="imput_dir", default=None)
    parser.add_argument("-j", dest="json_db", default=None)
    parser.add_argument("-a", dest="airports_file", default=None)
    parser.add_argument("-o", dest="output_db", default=None)
    parser.add_argument("-q", dest="queries_file", default=None)
    parser.add_argument("-r", dest="response_dir", default=".")
    return parser

def errors_log(log_path: str, error_messages: list[str]) -> None:
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
    try:
        for msg in error_messages:
            logger.warning(msg)
    finally:
        logger.removeHandler(handler)
        handler.close()

def is_valid_flight(data: object) -> bool:
    if not isinstance(data, list):
        return False
    required_keys = {
        "flight_id", "origin", "destination", "departure_datetime", "arrival_datetime", "price",
    }
    for item in data:
        if not isinstance(item, dict) or set(item.keys()) != required_keys:
            return False
    return True



def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2).

    argv is the argument list without the program name.
    None means use sys.argv[1:] (argparse does this for you).
    Do not call sys.exit() inside main(); return the code instead.
    """
    args_to_parse = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    try:
        args = parser.parse_args(args_to_parse)
    except SystemExit as exc:
        return 0 if exc.code in (0, None) else 2
    except ArgumentParserError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return exc.code
    sources = [
        s
        for s in (args.input.file, args.input.dir, args.json_db)
        if s is not None
    ]
    if len(sources) == 0:
        print("Error: Exactly one of -i, -d, or -j is required.", file=sys.stderr)
        return 2
    if len(sources) > 1:
        print("Error: Only one of -i, -d, or -j may be provided.", file=sys.stderr)
        return 2
    is_csv_mode = args.input_file is not None or args.input_dir is not None
    if is_csv_mode and not args.airports_file:
        print("Error: -a is required with -i or -d.", file=sys.stderr)
        return 2
    if not is_csv_mode and args.output_db is not None:
        print("Error: -o cannot be used with -j.", file=sys.stderr)
        return 2
    db_records: list[dict] = []
    if is_csv_mode:
        if not os.path.isfile(args.airports_file):
            print(f"Error: Airport file not found: {args.airports_file}", file=sys.stderr)
            return
        if args.input_file is not None:
            if not os.path.isfile(args.input_file):
                print(f"Error: Input CSV file not found: {args.input_file}", file=sys.stderr)
            return 1
            csv_paths = [args.input_file]
        else: 
            if not os.path.isdir(args.input_dir):
                print(f"Error: Input directory not found: {args.input_dir}", file =sys.stderr)
                return 1
            try:
                entries = os.listdir(args.input_dir)
            except OSError as exc:
                print(f"Error: Cannot read directory {args.input_dir}: {exc}", file=sys.stderr)
                return 1
            csv_paths = sorted(
                os.path.join(args.input_dir, name)
                for name in entries
                if name.endswith(".csv")
                and os.path.isfile(os.path.join(args.input_dir, name))
            )
            if not csv_paths:
                print(f"Error: no .csv files found in directory: {args.input_dir}", file = sys.stderr)
                return 1
        try:
            airports = load_airports(args.airports_file)
            db_records, error_messages = parse_files(csv_paths, airports)
        except OSError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        out_db_path = args.output_db if args.output_db is not None else "db.json"
        out_dir = os.path.dirname(os.path.abspath(out_db_path))
        log_path = os.path.join(out_dir, "errors.log")

        try:
            errors_log(log_path, error_messages)
            with open(out_db_path, "w", encoding="utf-8") as f:
                json.dump(db_records, f, indent = 2)
        except OSError as exc:
            print(f"Error: Failed to write output files: {exc}", file = sys.stderr)
            return 1
    else:
        if not os.path.isfile(args.json_db):
            print(f"Error: JSON database not found: {args.json_db}", file=sys.stderr)
            return 1
        try:
            with open(args.json_db, "r", encoding="utf-8") as f:
                loaded_db = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: Failed to load JSON database: {exc}", file=sys.stderr)
            return 1
        if not is_valid_flight(loaded_db):
            print("Error: JSON database has an invalid shape.", file=sys.stderr)
            return 1
        db_records = loaded_db
    if args.queries_file is not None:
        if not os.path.isfile(args.queries_file):
            print(f"Error: Queries file not found: {args.queries_file}", file=sys.stderr)
            return 1
        try:
            with open(args.queries_file, "r", encoding="utf-8") as f:
                queries_data = json.load(f)
        except (OSError, json.JSONDecodeError) as excc:
            print(f"Error: Failed to load queries JSON: {exc}")
            return 1
        if not isinstance(queries_data, (dict,list)):
            print("Error: Queries JSON must be an object or an array.", file=sys.stderr)
            return 1
        
        results = run_queries(db_records, queries_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        response_filename = (f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{timestamp}.json")
        response_path = os.path.join(args.response_dir, response_filename)

        try:
            with open(response_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        except OSError as exc:
            print(f"Error: Failed to write response file: {exc}", file=sys.stderr)
            return 1
    return 0
    raise NotImplementedError("main() is not written yet")

if __name__ == "__main__":
    sys.exit(main())
