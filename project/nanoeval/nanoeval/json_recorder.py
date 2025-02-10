import dataclasses
import json
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Literal, Self

import chz
from nanoeval.eval import EvalSpec
from nanoeval.fs_paths import get_package_root
from nanoeval.recorder_protocol import BasicRunSpec, RecorderConfig, RecorderProtocol


@dataclass
class JsonRecorder(RecorderProtocol):
    run_spec: BasicRunSpec  # type: ignore
    file_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    filename: Path
    sample_id: str | None = None
    group_id: str | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def __post_init__(self) -> None:
        self._write_record("run_started", {"run_spec": dataclasses.asdict(self.run_spec)})

    def current_sample_id(self) -> str | None:
        return self.sample_id

    def current_group_id(self) -> str | None:
        return self.group_id

    @contextmanager
    def as_default_recorder(
        self, sample_id: str, group_id: str, **extra: Any
    ) -> Generator[None, None, None]:
        old_sample_id = self.sample_id
        old_group_id = self.group_id
        self.sample_id = sample_id
        self.group_id = group_id
        try:
            yield
        finally:
            self.sample_id = old_sample_id
            self.group_id = old_group_id

    def _write_record(self, record_type: str, data: dict[str, Any]) -> None:
        record = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "record_type": record_type,
            "sample_id": self.sample_id,
            "group_id": self.group_id,
            **data,
        }
        with self.file_lock:
            with open(self.filename, "a", encoding="utf-8", errors="replace") as f:
                json_str = json.dumps(record, ensure_ascii=False)
                f.write(json_str + "\n")

    def record_match(
        self,
        correct: bool,
        *,
        expected: Any = None,
        picked: Any = None,
        prob_correct: Any = None,
        **extra: Any,
    ) -> None:
        self._write_record(
            "match",
            {
                "correct": correct,
                "expected": expected,
                "picked": picked,
                "prob_correct": prob_correct,
                **extra,
            },
        )

    def record_sampling(
        self,
        prompt: Any,
        sampled: Any,
        *,
        extra_allowed_metadata_fields: list[str] | None = None,
        **extra: Any,
    ) -> None:
        self._write_record(
            "sampling",
            {
                "prompt": prompt,
                "sampled": sampled,
                **extra,
            },
        )

    def record_sample_completed(self, **extra: Any) -> None:
        self._write_record(
            "sample_completed",
            {
                "status": "completed",
                **extra,
            },
        )

    def record_error(self, msg: str, error: Exception | None, **kwargs: Any) -> None:
        self._write_record(
            "error",
            {
                "message": msg,
                "error": str(error) if error else None,
                **kwargs,
            },
        )

    def record_extra(self, data: Any) -> None:
        self._write_record("extra", {"data": data})

    def record_final_report(self, final_report: Any) -> None:
        self._write_record("final_report", {"final_report": final_report})

    def evalboard_url(self, view: Literal["run", "monitor"]) -> str | None:
        return None


@chz.chz
class JsonRecorderConfig(RecorderConfig):
    filename: Path

    async def factory(self, spec: EvalSpec, num_tasks: int) -> RecorderProtocol:
        return JsonRecorder(run_spec=self._make_default_run_spec(spec), filename=self.filename)


def json_recorder() -> RecorderConfig:
    """
    Returns a recorder that writes results to a JSON Lines (.jsonl) file.
    """

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_T_%H-%M-%S_UTC")
    records_dir = Path(os.getenv("NANOEVAL_LOG_DIR", get_package_root() / "records"))
    records_dir.mkdir(parents=True, exist_ok=True)
    filename = records_dir / f"{timestamp}.jsonl"

    return JsonRecorderConfig(filename=filename)
