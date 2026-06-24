from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MUSIC_ANALYSIS_DIR = ROOT / "scripts" / "music_analysis"
if str(MUSIC_ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(MUSIC_ANALYSIS_DIR))

from prototype import analyze_pair  # type: ignore

from .agents.local_agents import (
    DynamicsAgent,
    ReflectionPromptAgent,
    RubatoTimingAgent,
    SignalOverviewAgent,
    StructureAlignmentAgent,
)
from .agents.synthesis_agent import OpenAISynthesisAgent
from .config import load_llm_profile
from .core import AgentResult, HarnessContext, read_json, timed_run, write_json


LOCAL_AGENTS = [
    SignalOverviewAgent(),
    RubatoTimingAgent(),
    DynamicsAgent(),
    StructureAlignmentAgent(),
    ReflectionPromptAgent(),
]


def resolve_path(base: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def prepare_audio(input_path: str | Path, output_dir: Path, name: str) -> Path:
    source = Path(input_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Audio not found: {source}")
    suffix = source.suffix or ".mp3"
    target = output_dir / f"{name}{suffix}"
    if source != target:
        shutil.copy2(source, target)
    return target


def run_harness(
    expert_audio: str | Path,
    user_audio: str | Path,
    output_dir: str | Path,
    max_duration_sec: float | None = 180.0,
    dtw_step: int = 6,
    segments: int = 48,
    use_openai: bool = True,
    openai_model: str | None = None,
    llm_config: str | Path | None = None,
    llm_profile: str | None = None,
) -> dict[str, Any]:
    start = time.time()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    expert_path = prepare_audio(expert_audio, output_dir, "expert")
    user_path = prepare_audio(user_audio, output_dir, "user")
    analysis_dir = output_dir / "signal_analysis"

    analyze_pair(
        expert_path=expert_path,
        user_path=user_path,
        output_dir=analysis_dir,
        n_segments=segments,
        max_duration_sec=max_duration_sec,
        dtw_step=dtw_step,
    )
    analysis = read_json(analysis_dir / "analysis.json")
    resolved_profile = load_llm_profile(llm_config, llm_profile)
    synthesis_model = resolved_profile.model_for("synthesis", openai_model)

    context = HarnessContext(
        expert_path=expert_path,
        user_path=user_path,
        output_dir=output_dir,
        analysis=analysis,
        analysis_dir=analysis_dir,
        project_root=ROOT,
        options={
            "max_duration_sec": max_duration_sec,
            "dtw_step": dtw_step,
            "segments": segments,
            "use_openai": use_openai,
            "llm": resolved_profile.redacted("synthesis", openai_model),
        },
    )

    agent_results: list[AgentResult] = []
    for agent in LOCAL_AGENTS:
        agent_results.append(timed_run(agent, context))

    synth_agent = OpenAISynthesisAgent(
        model=synthesis_model,
        enabled=use_openai,
        llm_profile=resolved_profile,
    )
    synth_start = time.time()
    synth_result = synth_agent.run_with_results(context, agent_results)
    synth_result.elapsed_sec = time.time() - synth_start
    agent_results.append(synth_result)

    run_data = {
        "expert_audio": str(expert_path),
        "user_audio": str(user_path),
        "output_dir": str(output_dir),
        "analysis_dir": str(analysis_dir),
        "analysis": analysis,
        "elapsed_sec": time.time() - start,
        "options": context.options,
        "agents": [result.__dict__ for result in agent_results],
        "final_report": synth_result.summary,
        "artifacts": collect_artifacts(output_dir, analysis_dir),
    }
    write_json(output_dir / "run.json", run_data)
    (output_dir / "final_report.md").write_text(synth_result.summary, encoding="utf-8-sig")
    return run_data


def collect_artifacts(output_dir: Path, analysis_dir: Path) -> dict[str, str]:
    names = [
        "01_waveform_rms.png",
        "02_tempo_curves.png",
        "03_dynamic_curves.png",
        "04_alignment_segments.png",
        "05_expressive_radar.png",
        "analysis.json",
        "segment_analysis.csv",
        "report.md",
    ]
    artifacts = {}
    for name in names:
        path = analysis_dir / name
        if path.exists():
            artifacts[name] = str(path)
    artifacts["run.json"] = str(output_dir / "run.json")
    artifacts["final_report.md"] = str(output_dir / "final_report.md")
    return artifacts


def agent_results_markdown(run_data: dict[str, Any]) -> str:
    lines = []
    for result in run_data.get("agents", []):
        lines.append(f"## {result['title']} `{result['status']}`")
        lines.append("")
        lines.append(result.get("summary", ""))
        lines.append("")
        evidence = result.get("evidence", {})
        if evidence:
            lines.append("```json")
            lines.append(json.dumps(evidence, ensure_ascii=False, indent=2)[:6000])
            lines.append("```")
            lines.append("")
    return "\n".join(lines)
