"""Common CSV/JSONL schema and deterministic, text-disjoint splitting."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path

from . import LABELS


@dataclass(frozen=True)
class Record:
    record_id: str
    text: str
    label: str | None = None


def load_records(path: str | Path, *, require_labels: bool = False) -> list[Record]:
    path = Path(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".csv":
            rows = list(csv.DictReader(stream))
        elif path.suffix.lower() == ".jsonl":
            rows = [json.loads(line) for line in stream if line.strip()]
        else:
            raise ValueError("Input must be a CSV or JSONL file")
    records: list[Record] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or not isinstance(row.get("text"), str):
            raise ValueError(f"Row {index}: text must be a string")
        text = row["text"].strip()
        if not text:
            raise ValueError(f"Row {index}: text must not be empty")
        record_id = row.get("record_id") or f"row-{index}"
        if not isinstance(record_id, str) or record_id in seen:
            raise ValueError(f"Row {index}: record_id must be a unique string")
        label = row.get("label") or None
        if label is not None and label not in LABELS:
            raise ValueError(f"Row {index}: label is outside the fixed label set")
        if require_labels and label is None:
            raise ValueError(f"Row {index}: label is required")
        seen.add(record_id)
        records.append(Record(record_id, text, label))
    if not records:
        raise ValueError("Input contains no records")
    return records


def stratified_split(
    records: list[Record], validation_fraction: float = 0.25, seed: int = 42
) -> tuple[list[Record], list[Record]]:
    """Split before any vectorizer/model fitting; reject duplicate normalized text."""
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    groups = {label: [] for label in LABELS}
    seen_text: set[str] = set()
    for record in records:
        if record.label not in groups:
            raise ValueError("Training requires a valid label for every record")
        normalized = " ".join(record.text.split()).casefold()
        if normalized in seen_text:
            raise ValueError("Duplicate normalized text must be resolved before splitting")
        seen_text.add(normalized)
        groups[record.label].append(record)
    rng = random.Random(seed)
    train, validation = [], []
    for label in LABELS:
        group = groups[label][:]
        if len(group) < 2:
            raise ValueError("Splitting requires at least two records per label")
        rng.shuffle(group)
        count = min(len(group) - 1, max(1, round(len(group) * validation_fraction)))
        validation.extend(group[:count])
        train.extend(group[count:])
    rng.shuffle(train)
    rng.shuffle(validation)
    return train, validation


def write_jsonl(path: str | Path, rows: list[dict]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def public_prediction(record: Record, prediction: str | None, **details) -> dict:
    """Keep the original text out of generated prediction artifacts."""
    return {
        "record_id": record.record_id,
        "expected_label": record.label,
        "prediction": prediction,
        **details,
    }
