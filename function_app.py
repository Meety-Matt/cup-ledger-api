"""Cup Ledger API - Azure Functions (Python v2 programming model).

Tracks the champion of each season of our Sleeper fantasy league.
All routes require an API key in the `x-api-key` request header.
"""
import hmac
import json
import logging
import os
from functools import wraps

import azure.functions as func

from repository import build_seeded_repository
from validation import validate_champion
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from datetime import datetime, timezone

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
repo = build_seeded_repository()


# ---------- helpers ----------

def json_response(body, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body), status_code=status, mimetype="application/json"
    )


def error_response(status: int, message: str, details=None) -> func.HttpResponse:
    payload = {"error": message}
    if details:
        payload["details"] = details
    return json_response(payload, status)


_api_key_cache = None


def _load_api_key():
    """Read the expected API key from Key Vault, once per process.

    Returns None if the vault can't be reached, which makes the API reject
    every request (fail closed) instead of letting anyone in.
    """
    global _api_key_cache
    if _api_key_cache is not None:
        return _api_key_cache

    vault_url = os.environ.get("KEY_VAULT_URL")
    if not vault_url:
        logging.error("KEY_VAULT_URL is not set. Rejecting all requests.")
        return None
    try:
        client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        _api_key_cache = client.get_secret("ApiKey").value
        return _api_key_cache
    except Exception:
        logging.exception("Could not read ApiKey from Key Vault. Rejecting all requests.")
        return None


def require_api_key(handler):
    """Reject any request without a valid x-api-key header (401).

    The expected key is read from the ApiKey secret in Key Vault.
    """

    @wraps(handler)
    def wrapper(req: func.HttpRequest) -> func.HttpResponse:
        expected = _load_api_key()
        provided = req.headers.get("x-api-key", "")
        if not expected or not hmac.compare_digest(provided, expected):
            logging.warning("Rejected request to %s: missing or invalid API key", req.url)
            return error_response(401, "Missing or invalid API key.")
        return handler(req)

    return wrapper


def parse_body(req: func.HttpRequest):
    """Return (body, error_response). Exactly one of the two is None."""
    try:
        return req.get_json(), None
    except ValueError:
        return None, error_response(400, "Request body must be valid JSON.")


# ---------- collection routes: /api/champions ----------

@app.route(route="champions", methods=["GET", "POST", "DELETE"])
@require_api_key
def champions_collection(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "GET":
        manager = req.params.get("manager")
        return json_response(repo.list(manager))

    if req.method == "POST":
        body, err = parse_body(req)
        if err:
            return err
        data, errors = validate_champion(body)
        if errors:
            return error_response(400, "Validation failed.", errors)
        if repo.season_taken(data["season"]):
            return error_response(
                409, f"A champion for season {data['season']} already exists."
            )
        return json_response(repo.create(data), 201)

    # DELETE /api/champions -> purge everything (optional enhancement)
    removed = repo.purge()
    logging.info("Purged %d champions", removed)
    return json_response({"message": "Repository purged.", "removed": removed})


# ---------- /api/champions/count (optional enhancement) ----------

@app.route(route="champions/count", methods=["GET"])
@require_api_key
def champions_count(req: func.HttpRequest) -> func.HttpResponse:
    return json_response({"count": repo.count()})


# ---------- item routes: /api/champions/{id} ----------

@app.route(route="champions/{id}", methods=["GET", "PUT", "DELETE"])
@require_api_key
def champion_item(req: func.HttpRequest) -> func.HttpResponse:
    champion_id = req.route_params.get("id", "")
    existing = repo.get(champion_id)
    if existing is None:
        return error_response(404, f"Champion '{champion_id}' not found.")

    if req.method == "GET":
        return json_response(existing)

    if req.method == "PUT":
        body, err = parse_body(req)
        if err:
            return err
        data, errors = validate_champion(body)
        if errors:
            return error_response(400, "Validation failed.", errors)
        if repo.season_taken(data["season"], exclude_id=champion_id):
            return error_response(
                409, f"A champion for season {data['season']} already exists."
            )
        return json_response(repo.update(champion_id, data))

    # DELETE
    repo.delete(champion_id)
    return json_response({"message": "Champion deleted.", "id": champion_id})

# ---------- batch validation: PATCH /api/champions/validate ----------

@app.route(route="champions/validate", methods=["PATCH"])
@require_api_key
def validate_champions(req: func.HttpRequest) -> func.HttpResponse:
    updated = repo.validate_all()
    logging.info("ValidationTriggered updatedCount=%d", updated)
    return json_response({
        "updatedCount": updated,
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "rule": "needsReview is true when pointsFor or record is missing",
    })