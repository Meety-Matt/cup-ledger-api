"""Champion storage backed by Azure Table Storage.

Records live in the "Champions" table of the storage account named by the
TABLE_ACCOUNT_NAME setting. Authentication uses DefaultAzureCredential: the
Function App's managed identity in Azure, or your az login on your computer.
No keys are stored in code or settings.
"""
import logging
import os
import uuid

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient, UpdateMode
from azure.identity import DefaultAzureCredential

TABLE_NAME = "Champions"
PARTITION = "champion"
FIELDS = (
    "season", "manager", "teamName", "record", "pointsFor",
    "runnerUp", "plaqueEngraved", "notes", "sleeperLeagueId",
)

# Seed data, loaded only when the table is empty.
# Paste every entry from your old build_seeded_repository() here.
SEED_CHAMPIONS = [
    {
        "season": 2025,
        "manager": "Chris",
        "teamName": "Post Mahomes",
        "record": "11-7",
        "pointsFor": 2297.84,
        "runnerUp": "Blude",
        "plaqueEngraved": False,
        "notes": "Beat Blude in the Chip, traded a lot of picks to win this year.",
    },
    {
        "season": 2024,
        "manager": "Kerz",
        "teamName": "Team Kerz",
        "record": "9-5",
        "pointsFor": 0,
        "runnerUp": "Tyler",
        "plaqueEngraved": True,
        "notes": "Pre Sleeper - Data Limited",
    },
    {
        "season": 2023,
        "manager": "Blude",
        "teamName": "The Blue Crew",
        "record": "7-7",
        "pointsFor": 0,
        "runnerUp": "Chris",
        "plaqueEngraved": True,
        "notes": "Pre Sleeper - Data Limited",
    },
    {
        "season": 2022,
        "manager": "Kerz",
        "teamName": "Team Kerz",
        "record": "10-4",
        "pointsFor": 0,
        "runnerUp": "",
        "plaqueEngraved": True,
        "notes": "Pre Sleeper - Data Limited",
    }
]


def _to_entity(champion_id, data):
    """Convert champion fields to a table entity. Empty fields are left out,
    because Table Storage doesn't store null properties."""
    entity = {"PartitionKey": PARTITION, "RowKey": champion_id}
    for field in FIELDS:
        value = data.get(field)
        if value is not None:
            entity[field] = value
    return entity


def _to_champion(entity):
    """Convert a table entity back to the dict shape the API returns."""
    champion = {"id": entity["RowKey"]}
    for field in FIELDS:
        champion[field] = entity.get(field)
    champion["plaqueEngraved"] = bool(champion["plaqueEngraved"])
    return champion


def _connect():
    account = os.environ.get("TABLE_ACCOUNT_NAME")
    if not account:
        raise RuntimeError(
            "TABLE_ACCOUNT_NAME is not set. Add it to local.settings.json "
            "and to the Function App's Environment variables."
        )
    service = TableServiceClient(
        endpoint=f"https://{account}.table.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    service.create_table_if_not_exists(TABLE_NAME)
    return service.get_table_client(TABLE_NAME)


class ChampionRepository:
    def __init__(self, table_client):
        self._table = table_client

    @staticmethod
    def _valid_id(champion_id):
        """Return the normalized GUID, or None if the text isn't a GUID."""
        try:
            return str(uuid.UUID(str(champion_id)))
        except ValueError:
            return None

    def _all_entities(self, select=None):
        return self._table.query_entities(
            query_filter="PartitionKey eq @pk",
            parameters={"pk": PARTITION},
            select=select,
        )

    def list(self, manager=None):
        champions = [_to_champion(e) for e in self._all_entities()]
        if manager:
            champions = [
                c for c in champions
                if (c["manager"] or "").lower() == manager.lower()
            ]
        return sorted(champions, key=lambda c: c["season"] or 0, reverse=True)

    def get(self, champion_id):
        key = self._valid_id(champion_id)
        if key is None:
            return None
        try:
            return _to_champion(self._table.get_entity(PARTITION, key))
        except ResourceNotFoundError:
            return None

    def season_taken(self, season, exclude_id=None):
        entities = self._table.query_entities(
            query_filter="PartitionKey eq @pk and season eq @season",
            parameters={"pk": PARTITION, "season": season},
        )
        return any(e["RowKey"] != exclude_id for e in entities)

    def create(self, data, champion_id=None):
        new_id = champion_id or str(uuid.uuid4())
        entity = _to_entity(new_id, data)
        self._table.create_entity(entity)
        return _to_champion(entity)

    def update(self, champion_id, data):
        key = self._valid_id(champion_id)
        if key is None or self.get(key) is None:
            return None
        entity = _to_entity(key, data)
        # REPLACE matches PUT semantics: optional fields left out are cleared.
        self._table.upsert_entity(entity, mode=UpdateMode.REPLACE)
        return _to_champion(entity)

    def delete(self, champion_id):
        key = self._valid_id(champion_id)
        if key is None:
            return None
        try:
            self._table.delete_entity(PARTITION, key)
            return {"id": key}
        except ResourceNotFoundError:
            return None

    def purge(self):
        keys = [
            (e["PartitionKey"], e["RowKey"])
            for e in self._all_entities(select=["PartitionKey", "RowKey"])
        ]
        for partition, row in keys:
            self._table.delete_entity(partition, row)
        return len(keys)

    def count(self):
        return sum(1 for _ in self._all_entities(select=["RowKey"]))


def build_seeded_repository():
    """Connect to the table and load seed champions only if it's empty.

    Restarts keep your data. Seed records return only after a purge
    leaves the table empty.
    """
    repo = ChampionRepository(_connect())
    if repo.count() == 0:
        for sample in SEED_CHAMPIONS:
            stable_id = str(uuid.uuid5(
                uuid.NAMESPACE_DNS, f"cup-ledger-{sample['season']}"
            ))
            repo.create(sample, champion_id=stable_id)
        logging.info("Seeded %d champions", len(SEED_CHAMPIONS))
    return repo