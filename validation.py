"""Request-body validation for Champion resources."""
from datetime import date

FIRST_SEASON = 1995  # the Braggart's Cup tradition starts here


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_champion(body) -> tuple[dict, list[str]]:
    """Validate a full Champion body (used by POST and PUT).

    Returns (clean_data, errors). If errors is non-empty the request is a 400.
    """
    if not isinstance(body, dict):
        return {}, ["Request body must be a JSON object."]

    errors: list[str] = []
    clean: dict = {}

    # --- required fields ---
    season = body.get("season")
    max_season = date.today().year + 1
    if not isinstance(season, int) or isinstance(season, bool):
        errors.append("'season' is required and must be an integer.")
    elif not FIRST_SEASON <= season <= max_season:
        errors.append(f"'season' must be between {FIRST_SEASON} and {max_season}.")
    else:
        clean["season"] = season

    for field in ("manager", "teamName"):
        value = body.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"'{field}' is required and must be a non-empty string.")
        else:
            clean[field] = value.strip()

    # --- optional fields ---
    for field in ("record", "runnerUp", "notes", "sleeperLeagueId"):
        value = body.get(field)
        if value is None:
            clean[field] = None
        elif not isinstance(value, str):
            errors.append(f"'{field}' must be a string if provided.")
        else:
            clean[field] = value.strip()

    points = body.get("pointsFor")
    if points is None:
        clean["pointsFor"] = None
    elif not _is_number(points) or points < 0:
        errors.append("'pointsFor' must be a non-negative number if provided.")
    else:
        clean["pointsFor"] = points

    plaque = body.get("plaqueEngraved", False)
    if not isinstance(plaque, bool):
        errors.append("'plaqueEngraved' must be true or false if provided.")
    else:
        clean["plaqueEngraved"] = plaque

    return clean, errors
