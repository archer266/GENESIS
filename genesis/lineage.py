"""Bounded observational birth archive. No RNG, graphics or ecosystem decisions."""
from dataclasses import asdict, dataclass, replace
import csv
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .simulation import Traits


ARCHIVE_LIMIT = 4096
CAUSES = ("energy", "age", "caught")


@dataclass(frozen=True)
class LineageRecord:
    id: int
    species: str
    parent_id: int | None
    generation: int
    birth_time: float | None
    traits: "Traits"
    recorded_time: float
    origin: str = "birth"
    death_time: float | None = None
    death_cause: str | None = None


class LineageArchive:
    """Keep every living record, then newest dead records by birth ID.

    Only dead records can be pruned. Missing IDs are never reconstructed;
    legacy_unavailable counts records absent when migrating an older world.
    """
    def __init__(self, capacity=ARCHIVE_LIMIT):
        self.capacity = capacity
        self._records = {}
        self.pruned_count = 0
        self.legacy_unavailable = 0
        self.revision = 0

    @property
    def records(self):
        return MappingProxyType(self._records)

    def record_birth(self, organism, when, legacy=False):
        if organism.id in self._records:
            raise ValueError("A birth record cannot be overwritten")
        self._records[organism.id] = LineageRecord(
            organism.id, organism.species, organism.parent_id, organism.generation,
            None if legacy else when, organism.traits, when,
            "legacy_snapshot" if legacy else "birth")
        self.revision += 1
        self._prune()

    def record_death(self, oid, when, cause):
        record = self._records.get(oid)
        if record is None or record.death_time is not None:
            return
        if cause not in CAUSES:
            raise ValueError("Unknown death cause")
        # Replace lifecycle fields only. Existing immutable birth snapshots stay valid.
        self._records[oid] = replace(record, death_time=when, death_cause=cause)
        self.revision += 1
        self._prune()

    def _prune(self):
        if len(self._records) <= self.capacity:
            return
        for oid in list(self._records):
            if self._records[oid].death_time is not None:
                del self._records[oid]
                self.pruned_count += 1
                if len(self._records) <= self.capacity:
                    break

    def ancestry(self, oid):
        """Viewed record first, stopping at a founder or the first unavailable ID."""
        rows, seen = [], set()
        while oid is not None and oid not in seen:
            seen.add(oid)
            record = self._records.get(oid)
            rows.append((oid, record))
            if record is None:
                break
            oid = record.parent_id
        return rows

    def offspring(self, oid):
        return [r for r in self._records.values() if r.parent_id == oid]

    def changes(self, oid):
        child = self._records.get(oid)
        parent = self._records.get(child.parent_id) if child else None
        if not parent or child.origin != "birth" or parent.origin != "birth":
            return None
        return {name: getattr(child.traits, name)-getattr(parent.traits, name)
                for name in ("speed", "sense", "size")}

    def document(self, *, defer_records=False):
        return {"capacity": self.capacity, "pruned_count": self.pruned_count,
                "legacy_unavailable": self.legacy_unavailable,
                "records": list(self._records.values()) if defer_records else [asdict(r) for r in self._records.values()]}

    def export_csv(self, path, settings):
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        names = ["id", "species", "parent_id", "generation", "birth_time", "origin",
                 "recorded_time", "speed", "sense", "size", "death_time", "death_cause",
                 "status", "parent_record_available", "birth_traits_known", "delta_speed", "delta_sense", "delta_size"]
        metadata = asdict(settings)
        metadata.update(archive_limit=self.capacity, pruned_records=self.pruned_count,
                        legacy_unavailable_records=self.legacy_unavailable)
        with path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=[*metadata, *names])
            writer.writeheader()
            for record in self._records.values():
                row = asdict(record)
                row.update(row.pop("traits"))
                changes = self.changes(record.id)
                row.update(status="dead" if record.death_time is not None else "living",
                           parent_record_available=record.parent_id in self._records,
                           birth_traits_known=record.origin == "birth",
                           **{"delta_"+k: changes[k] if changes else None for k in ("speed", "sense", "size")})
                writer.writerow({**metadata, **row})
        return path
