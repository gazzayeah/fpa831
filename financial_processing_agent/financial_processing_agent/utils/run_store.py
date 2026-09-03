"""SQLite persistence so a run can be inspected, resumed, and approval-replayed after restart."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from financial_processing_agent.shared_libraries.settings import settings
from financial_processing_agent.state.run_state import RunState


def _connect(path: Path | None = None) -> sqlite3.Connection:
    """Open (or create) the runs table. Path defaults to settings.resolved_run_store_path."""
    store = path or settings.resolved_run_store_path
    store.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(store)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


class RunStore:
    """Insert-or-replace JSON blobs keyed by run_id."""

    def __init__(self, path: Path | None = None) -> None:
        """Use ``path`` in tests; production defaults to ``settings.resolved_run_store_path``."""
        self.path = path or settings.resolved_run_store_path

    def save(self, state: RunState) -> None:
        """Persist the full RunState (including audit)."""
        conn = _connect(self.path)
        conn.execute(
            "INSERT OR REPLACE INTO runs(run_id, payload) VALUES (?, ?)",
            (state.run_id, state.model_dump_json()),
        )
        conn.commit()
        conn.close()

    def get(self, run_id: str) -> RunState | None:
        """Load a run or return None."""
        conn = _connect(self.path)
        row = conn.execute(
            "SELECT payload FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        conn.close()
        if not row:
            return None
        return RunState.model_validate(json.loads(row[0]))

    def list_ids(self) -> list[str]:
        """All stored run ids (for debugging)."""
        conn = _connect(self.path)
        rows = conn.execute("SELECT run_id FROM runs").fetchall()
        conn.close()
        return [r[0] for r in rows]
