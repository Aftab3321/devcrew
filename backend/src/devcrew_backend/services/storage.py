import json
import threading
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel


class Session:
    """Session-local blackboard memory and append-only event/handoff records."""

    # Create an isolated run directory and save its request metadata.
    def __init__(self, base: Path, requirements: str, mode: str):
        self.id = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "_"
            + uuid4().hex[:12]
        )
        self.path = base / self.id
        self.path.mkdir(parents=True, exist_ok=False)
        self.lock = threading.RLock()
        self.memory = {}
        self.write(
            "request.json",
            {"requirements": requirements, "mode": mode, "session_id": self.id},
        )

    # Write a named session artifact and replace JSON files atomically.
    def write(self, name, value):
        if Path(name).name != name:
            raise ValueError("Artifact names must be simple filenames")
        if isinstance(value, BaseModel):
            value = value.model_dump()
        with self.lock:
            target = self.path / name
            if name.endswith(".json"):
                temporary = target.with_suffix(target.suffix + ".tmp")
                temporary.write_text(
                    json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                os.replace(temporary, target)
            else:
                target.write_text(value, encoding="utf-8")

    # Append a timestamped activity record to the session log.
    def event(self, kind, **data):
        with self.lock:
            with (self.path / "events.jsonl").open("a", encoding="utf-8") as out:
                out.write(
                    json.dumps(
                        {
                            "time": datetime.now(timezone.utc).isoformat(),
                            "kind": kind,
                            **data,
                        }
                    )
                    + "\n"
                )

    # Save a named result to the session's shared blackboard.
    def remember(self, key, content):
        with self.lock:
            self.memory[key] = content
            self.write("memory.json", self.memory)

    # Read the current blackboard as serialized context.
    def recall(self):
        with self.lock:
            return json.dumps(self.memory, ensure_ascii=False)

    # Reopen an existing session directory in a worker process.
    @classmethod
    def attach(cls, path):
        obj = cls.__new__(cls)
        obj.path = Path(path)
        obj.id = obj.path.name
        obj.lock = threading.RLock()
        try:
            obj.memory = json.loads(
                (obj.path / "memory.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            obj.memory = {}
        return obj
