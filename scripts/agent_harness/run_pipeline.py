from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from agent_harness.harness import agent_results_markdown, run_harness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-agent piano analysis harness.")
    parser.add_argument("--expert", type=Path, default=ROOT / "files" / "case0" / "original.mp3")
    parser.add_argument("--user", type=Path, default=ROOT / "files" / "case0" / "user_ver.mp3")
    parser.add_argument("--output", type=Path, default=ROOT / "files" / "case0" / "agent_harness_output")
    parser.add_argument("--max-duration", type=float, default=180.0)
    parser.add_argument("--dtw-step", type=int, default=6)
    parser.add_argument("--segments", type=int, default=48)
    parser.add_argument("--no-openai", action="store_true")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--model", default=None, help="Override the synthesis model id from the selected profile.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_data = run_harness(
        expert_audio=args.expert,
        user_audio=args.user,
        output_dir=args.output,
        max_duration_sec=None if args.max_duration <= 0 else args.max_duration,
        dtw_step=args.dtw_step,
        segments=args.segments,
        use_openai=not args.no_openai,
        openai_model=args.model,
        llm_config=args.config,
        llm_profile=args.profile,
    )
    print("Agent harness complete")
    print(f"Output: {run_data['output_dir']}")
    print(f"Final report: {run_data['artifacts']['final_report.md']}")
    print("\n=== Agent summaries ===\n")
    print(agent_results_markdown(run_data)[:4000])


if __name__ == "__main__":
    main()
