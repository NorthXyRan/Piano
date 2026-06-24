from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class AgentResult:
    name: str
    title: str
    status: str
    summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    elapsed_sec: float = 0.0


@dataclass
class HarnessContext:
    expert_path: Path
    user_path: Path
    output_dir: Path
    analysis: dict[str, Any]
    analysis_dir: Path
    project_root: Path
    options: dict[str, Any] = field(default_factory=dict)


class Agent(Protocol):
    name: str
    title: str

    def run(self, context: HarnessContext) -> AgentResult:
        ...


def timed_run(agent: Agent, context: HarnessContext) -> AgentResult:
    start = time.time()
    try:
        result = agent.run(context)
        result.elapsed_sec = time.time() - start
        return result
    except Exception as exc:
        return AgentResult(
            name=agent.name,
            title=agent.title,
            status="error",
            summary=f"Agent failed: {exc}",
            evidence={"error": repr(exc)},
            elapsed_sec=time.time() - start,
        )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8-sig")


def fmt_delta(value: float, unit: str = "") -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}{unit}"


def classify_delta(value: float, small: float, medium: float) -> str:
    magnitude = abs(value)
    if magnitude < small:
        return "接近"
    if magnitude < medium:
        return "有差异"
    return "差异明显"
