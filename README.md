# Cup Ledger API

A small REST API (Azure Functions, Python) that records the champion of each season of our Sleeper fantasy league. Midterm project for CS432/CY-421 Cloud Computing.

Data is held in an in-memory repository and resets when the Function App restarts. This is expected for the midterm.

## Authentication
Every request needs an `x-api-key` header. The expected value comes from the `API_KEY` app setting. Missing or wrong keys get `401`.

## Endpoints
| Method | Route | Success | Errors |
|---|---|---|---|
| POST | `/api/champions` | 201 | 400, 401, 409 |
| GET | `/api/champions` (`?manager=`) | 200 | 401 |
| GET | `/api/champions/{id}` | 200 | 401, 404 |
| PUT | `/api/champions/{id}` | 200 | 400, 401, 404, 409 |
| DELETE | `/api/champions/{id}` | 200 | 401, 404 |
| DELETE | `/api/champions` (purge) | 200 | 401 |
| GET | `/api/champions/count` | 200 | 401 |

## Champion model
| Field | Type | Required |
|---|---|---|
| id | string (GUID, server-generated) | - |
| season | integer, 1995 to next year, unique | yes |
| manager | string | yes |
| teamName | string | yes |
| record | string, e.g. "11-3" | no |
| pointsFor | number >= 0 | no |
| runnerUp | string | no |
| plaqueEngraved | boolean (default false) | no |
| notes | string | no |
| sleeperLeagueId | string | no |

## Run locally
1. Use a project folder that is NOT synced by OneDrive/iCloud.
2. Create a venv and install dependencies: `pip install -r requirements.txt`
3. Copy `local.settings.json.example` to `local.settings.json` and set `API_KEY` to a long random value. This file is git-ignored.
4. `func start`, then call `http://localhost:7071/api/champions` with the header.

## Deploy to Azure
1. In VS Code, open the Azure extension, then Create Function App in Azure (Python, a version Azure Functions supports).
2. Deploy to Function App.
3. In the portal, open Function App > Environment variables and add `API_KEY` with a long random value, then save.
4. Base URL: `https://<your-app-name>.azurewebsites.net/api`
