from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class Journal:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.json_path = self.directory / "trades.jsonl"
        self.csv_path = self.directory / "trades.csv"
        self._csv_initialized = self.csv_path.exists()

    def record(self, entry: Dict[str, Any]) -> None:
        entry = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}
        with self.json_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        self._write_csv(entry)

    def _write_csv(self, entry: Dict[str, Any]) -> None:
        with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(entry.keys()))
            if not self._csv_initialized:
                writer.writeheader()
                self._csv_initialized = True
            writer.writerow(entry)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def log_event(logger: logging.Logger, message: str, **payload: Any) -> None:
    if payload:
        logger.info("%s | %s", message, json.dumps(payload, default=str))
    else:
        logger.info(message)


def serialize_dataclass(obj: Any) -> Dict[str, Any]:
    try:
        return asdict(obj)
    except TypeError:
        return {"value": obj}
