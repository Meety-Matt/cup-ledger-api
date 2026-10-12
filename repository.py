"""In-memory repository for Champion records.

Data lives only in this process's memory, so it is volatile: it resets whenever
the Function App restarts or is recycled. That is expected for the midterm.
The final project will swap this class for a persistent store.
"""
import threading
import uuid
from typing import Optional


class ChampionRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._lock = threading.Lock()

    def list(self, manager: Optional[str] = None) -> list[dict]:
        with self._lock:
            items = list(self._items.values())
        if manager:
            items = [c for c in items if c["manager"].lower() == manager.lower()]
        return sorted(items, key=lambda c: c["season"], reverse=True)

    def get(self, champion_id: str) -> Optional[dict]:
        with self._lock:
            return self._items.get(champion_id)

    def season_taken(self, season: int, exclude_id: Optional[str] = None) -> bool:
        with self._lock:
            return any(
                c["season"] == season and c["id"] != exclude_id
                for c in self._items.values()
            )

    def create(self, data: dict) -> dict:
        champion = {"id": str(uuid.uuid4()), **data}
        with self._lock:
            self._items[champion["id"]] = champion
        return champion

    def update(self, champion_id: str, data: dict) -> Optional[dict]:
        with self._lock:
            if champion_id not in self._items:
                return None
            champion = {"id": champion_id, **data}
            self._items[champion_id] = champion
            return champion

    def delete(self, champion_id: str) -> Optional[dict]:
        with self._lock:
            return self._items.pop(champion_id, None)

    def purge(self) -> int:
        with self._lock:
            count = len(self._items)
            self._items.clear()
            return count

    def count(self) -> int:
        with self._lock:
            return len(self._items)


def build_seeded_repository() -> ChampionRepository:
    repo = ChampionRepository()
    samples = [
        {
                    "season": 2022,
                    "manager": "Kerz",
                    "teamName": "Team Kerz",
                    "record": "10-4",
                    "pointsFor": 0,
                    "runnerUp": "",
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
            "season": 2025,
            "manager": "Chris",
            "teamName": "Post Mahomes",
            "record": "11-7",
            "pointsFor": 2297.84,
            "runnerUp": "Blude",
            "plaqueEngraved": False,
            "notes": "Beat Blude in the Chip, traded a lot of picks to win this year.",
        },
    ]
    for sample in samples:
        repo.create(sample)
    return repo
