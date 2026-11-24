"""Running queries against the flight database."""

from datetime import datetime
import math
_RECORD_KEYS = {
    "flight_id", "origin", "destination", "departure_datetime", "arrival_datetime", "price",
}

_ALLOWED_QUERY_KEYS = _RECORD_KEYS | {
    "min_price", "sort_by", "order", "limit",
}

DATETIME_FORMAT = "%Y-%m-%d %H:%M"

def is_number(value:object) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    )

def is_int(value: object) -> bool:
    return isinstance(value,int) and not isinstance(value,bool)

def parse_query_dt(value: object) -> datetime | None:
    if not isinstance(value,str):
        return None
    if len(value) != 16 or value[10] != " ":
        return None
    try:
        dt = datetime.strptime(value, DATETIME_FORMAT)
    except ValueError:
        return None
    if dt.strftime(DATETIME_FORMAT) != value:
        return None
    return dt

def _validate_query(query: object) -> bool:
    if not isinstance(query, dict):
        return False

    for key in query:
        if key not in _ALLOWED_QUERY_KEYS:
            return False

    if "flight_id" in query and not isinstance(query["flight_id"], str):
        return False

    if "origin" in query and not isinstance(query["origin"], str):
        return False

    if "destination" in query and not isinstance(query["destination"], str):
        return False

    if "departure_datetime" in query and parse_query_dt(query["departure_datetime"]) is None:
        return False

    if "arrival_datetime" in query and parse_query_dt(query["arrival_datetime"]) is None:
        return False

    if "price" in query and not is_number(query["price"]):
        return False

    if "min_price" in query and not is_number(query["min_price"]):
        return False

    if "sort_by" in query:
        if not isinstance(query["sort_by"], str) or query["sort_by"] not in _RECORD_KEYS:
            return False

    if "order" in query:
        if "sort_by" not in query:
            return False
        if not isinstance(query["order"], str) or query["order"] not in {"asc", "desc"}:
            return False

    if "limit" in query:
        if not is_int(query["limit"]) or query["limit"] < 0:
            return False

    return True

def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query:   {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not _validate_query(query):
        return {
            "query": query,
            "error": "INVALID_QUERY",
            "matches": [],
        }
    q_dep_dt = (
        parse_query_dt(query["departure_datetime"])
        if "departure_datetime" in query
        else None
    )
    q_arr_dt = (
        parse_query_dt(query["arrival_datetime"])
        if "arrival_datetime" in query
        else None
    )
    matches: list[dict] = []
    for rec in db:
        if "flight_id" in query and rec.get("flight_id") != query["flight_id"]:
            continue
        if "origin" in query and rec.get("origin") != query["origin"]:
            continue
        if "destination" in query and rec.get("destination") != query["destination"]:
            continue
        if q_dep_dt is not None:
            rec_dep_dt = parse_query_dt(rec.get("departure_datetime"))
            if rec_dep_dt is None or rec_dep_dt < q_dep_dt:
                continue
        if q_arr_dt is not None:
            rec_arr_dt = parse_query_dt(rec.get("arrival_datetime"))
            if rec_arr_dt is None or rec_arr_dt > q_arr_dt:
                continue
        if "price" in query and rec.get("price") > query["price"]:
            continue
        if "min_price" in query and rec.get("price") < query["min_price"]:
            continue
        matches.appent(dict(rec))
        if "sort_by" in query:
            sort_key = query["sort_by"]
            reverse = query.get("order","asc") == "desc"
            matches.sort(key=lambda item: item.get(sort_key), reverse=reverse)
        if "limit" in query:
            matches = matches[: query["limit"]]

    return{
        "query": query,
        "matches": matches,
    }
    raise NotImplementedError


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries,dict):
        query_list = [queries]
    elif isinstance(queries, list):
        query_list = queries
    else:
        return [
            {"query": "queries",
            "error": "INVALID_QUERY",
            "matches": []}
        ] 
    return [run_query(db, q) for q in query_list]
    raise NotImplementedError
