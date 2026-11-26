# Cup Ledger API

A small REST API that tracks the champion of each season of our Sleeper fantasy football league. Built with Python on Azure Functions for CS432/CY-421 Cloud Computing.

## What changed from the midterm

- Champions are stored in **Azure Table Storage** instead of memory, so data survives restarts.
- The API key is stored in **Azure Key Vault** and read through the Function App's managed identity.
- A new **batch validation** endpoint (`PATCH /api/champions/validate`) flags champions with missing data.
- A **Logic App** runs the validation on a schedule and sends an email with the result.
- **Application Insights** records requests, custom events, and dependency calls.

## Project files

- `function_app.py`: routes, API key check, and logging
- `repository.py`: reads and writes champions in Table Storage
- `validation.py`: checks the body of POST and PUT requests
- `host.json`, `requirements.txt`: Functions host settings and dependencies
- `local.settings.json.example`: template for local settings (no real values)

## Setup

### Prerequisites

- Python 3.13, Azure Functions Core Tools, and the Azure CLI
- An Azure subscription with a storage account, a Key Vault, and a Function App

### Run locally

1. Sign in to Azure: `az login`
2. Create a virtual environment and install dependencies:
3. Copy `local.settings.json.example` to `local.settings.json` and fill in your values:
   - `TABLE_ACCOUNT_NAME`: the storage account name
   - `KEY_VAULT_URL`: the vault URL, for example `https://your-vault.vault.azure.net/`
4. Your account needs the **Storage Table Data Contributor** role on the storage account and the **Key Vault Secrets User** role on the vault.
5. Start the app: `func start`

`local.settings.json` is git-ignored, so your values stay off GitHub.

### Deploy to Azure

1. Set the same `TABLE_ACCOUNT_NAME` and `KEY_VAULT_URL` values under the Function App's **Environment variables**.
2. Turn on the Function App's system-assigned identity, then give it **Storage Table Data Contributor** on the storage account and **Key Vault Secrets User** on the vault.
3. Store the API key as a secret named `ApiKey` in the vault.
4. Deploy with the Azure Functions extension in VS Code, or `func azure functionapp publish <app-name>`.

The resource group template in infra/resourcegroup-template.json is an export of the deployed resources. Replace the placeholder email and subscription ID before deploying. The ApiKey secret value is not included and must be set again in Key Vault.

## API key

Every endpoint requires the `x-api-key` header. The value must match the `ApiKey` secret in Key Vault. A missing or wrong key returns `401`.

## Endpoints

Base URL: `https://<your-app>.azurewebsites.net/api`

| Method | Route | Purpose |
|---|---|---|
| POST | `/champions` | Create a champion (201) |
| GET | `/champions` | List champions, newest season first. Optional `?manager=` filter |
| GET | `/champions/{id}` | Get one champion |
| PUT | `/champions/{id}` | Replace a champion |
| DELETE | `/champions/{id}` | Delete a champion |
| DELETE | `/champions` | Purge all champions |
| GET | `/champions/count` | Count champions |
| PATCH | `/champions/validate` | Run batch validation and return `updatedCount` and `validatedAt` |

Status codes: `200`, `201`, `400` (invalid body), `401` (bad key), `404` (not found), `409` (season already exists).

## Validation rule

A champion is flagged with `needsReview: true` when `pointsFor` or `record` is missing. The `PATCH /champions/validate` endpoint recalculates the flag for every champion and saves only the ones that changed. The response includes `updatedCount` and a UTC timestamp.

`needsReview` is set by the server and can't be set through POST or PUT.

## Documentation

The full project documentation, including test evidence and deployment notes, is in the submitted report.