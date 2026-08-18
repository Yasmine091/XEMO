"""Small durable journal for XEMO's browser life state.

This is deliberately not an autonomous brain. It preserves continuity when a
browser tab is suspended, while leaving perception, model calls, and physical
actions under their existing safety owners.
"""

import json
import os
import threading
import time
from pathlib import Path


class LifeStateStore:
    """Read/write a bounded, private checkpoint for one XEMO instance."""

    def __init__(self, path=None):
        default = os.environ.get("XEMO_LIFE_STATE", str(Path.home() / ".xemo-life-state.json"))
        self.path = Path(path or default).expanduser()
        self.lock = threading.RLock()
        self.state = self._read()

    @staticmethod
    def _clean_text(value, limit):
        return " ".join(str(value or "").split())[:limit]

    def _normalise(self, value):
        value = value if isinstance(value, dict) else {}
        lifecycle = value.get("lifeCycle") if isinstance(value.get("lifeCycle"), dict) else {}
        goal = value.get("activeGoal") if isinstance(value.get("activeGoal"), dict) else None
        return {
            "schema": 1,
            "updatedAt": float(value.get("updatedAt") or time.time()),
            "clientSeenAt": float(value.get("clientSeenAt") or time.time()),
            "lifeCycle": {
                "sequence": max(0, int(lifecycle.get("sequence") or 0)),
                "phase": self._clean_text(lifecycle.get("phase") or "resting", 24),
                "mode": self._clean_text(lifecycle.get("mode") or "idle", 24),
                "reason": self._clean_text(lifecycle.get("reason"), 180),
                "detail": self._clean_text(lifecycle.get("detail"), 220),
                "updatedAt": float(lifecycle.get("updatedAt") or 0),
            },
            "activeGoal": None if not goal else {
                "id": self._clean_text(goal.get("id"), 48),
                "kind": self._clean_text(goal.get("kind"), 32),
                "target": self._clean_text(goal.get("target"), 180),
                "status": self._clean_text(goal.get("status"), 100),
                "steps": max(0, int(goal.get("steps") or 0)),
                "maxSteps": max(1, int(goal.get("maxSteps") or 1)),
                "started": float(goal.get("started") or 0),
                "updatedAt": float(goal.get("updatedAt") or 0),
            },
            "taskPlan": {
                "status": self._clean_text((value.get("taskPlan") or {}).get("status") if isinstance(value.get("taskPlan"), dict) else "idle", 80),
                "target": self._clean_text((value.get("taskPlan") or {}).get("target") if isinstance(value.get("taskPlan"), dict) else "", 180),
            },
            "lastDream": float(value.get("lastDream") or 0),
        }

    def _read(self):
        try:
            return self._normalise(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return self._normalise({})

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))

    def update(self, value):
        with self.lock:
            incoming = self._normalise(value)
            current_sequence = int(self.state.get("lifeCycle", {}).get("sequence") or 0)
            incoming_sequence = int(incoming.get("lifeCycle", {}).get("sequence") or 0)
            if incoming_sequence < current_sequence:
                incoming["lifeCycle"] = self.state["lifeCycle"]
            self.state = incoming
            self._write()
            return self.snapshot()

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        temporary.replace(self.path)
