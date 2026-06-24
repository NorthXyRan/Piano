from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import gradio as gr

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from agent_harness.harness import agent_results_markdown, run_harness

DEFAULT_EXPERT = ROOT / "files" / "case0" / "original.mp3"
DEFAULT_USER = ROOT / "files" / "case0" / "user_ver.mp3"
DEFAULT_OUTPUT_BASE = ROOT / "files" / "gradio_runs"


def path_from_upload_or_text(upload: str | None, text: str) -> str:
    if upload:
        return upload
    return text.strip()


def run_ui(
    expert_upload: str | None,
    user_upload: str | None,
    expert_path_text: str,
    user_path_text: str,
    max_duration: float,
    segments: int,
    dtw_step: int,
    use_openai: bool,
    config_path: str,
    profile_name: str,
    model: str,
) -> tuple[str, str, str, str, str, str, str, str, list[str]]:
    expert = path_from_upload_or_text(expert_upload, expert_path_text)
    user = path_from_upload_or_text(user_upload, user_path_text)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = DEFAULT_OUTPUT_BASE / f"run_{stamp}"

    run_data = run_harness(
        expert_audio=expert,
        user_audio=user,
        output_dir=output_dir,
        max_duration_sec=None if max_duration <= 0 else float(max_duration),
        dtw_step=int(dtw_step),
        segments=int(segments),
        use_openai=bool(use_openai),
        openai_model=model.strip() or None,
        llm_config=config_path.strip() or None,
        llm_profile=profile_name.strip() or None,
    )

    artifacts = run_data["artifacts"]
    timeline_md = build_timeline(run_data)
    agents_md = agent_results_markdown(run_data)
    final_report = run_data["final_report"]
    metrics_json = json.dumps(slim_run_data(run_data), ensure_ascii=False, indent=2)
    files = [path for path in artifacts.values() if Path(path).exists()]

    return (
        timeline_md,
        final_report,
        agents_md,
        metrics_json,
        artifacts.get("01_waveform_rms.png", ""),
        artifacts.get("02_tempo_curves.png", ""),
        artifacts.get("03_dynamic_curves.png", ""),
        artifacts.get("04_alignment_segments.png", ""),
        files,
    )


def build_timeline(run_data: dict[str, Any]) -> str:
    lines = ["# Agent 运行过程", ""]
    for idx, result in enumerate(run_data.get("agents", []), 1):
        status = result.get("status", "unknown")
        elapsed = result.get("elapsed_sec", 0.0)
        lines.append(f"{idx}. **{result.get('title')}** - `{status}` - {elapsed:.2f}s")
        summary = result.get("summary", "").strip().replace("\n", " ")
        if len(summary) > 220:
            summary = summary[:220] + "..."
        lines.append(f"   {summary}")
    lines.append("")
    lines.append(f"总耗时：{run_data.get('elapsed_sec', 0):.2f}s")
    return "\n".join(lines)


def slim_run_data(run_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "expert_audio": run_data.get("expert_audio"),
        "user_audio": run_data.get("user_audio"),
        "output_dir": run_data.get("output_dir"),
        "elapsed_sec": run_data.get("elapsed_sec"),
        "options": run_data.get("options"),
        "agents": [
            {
                "name": item.get("name"),
                "status": item.get("status"),
                "elapsed_sec": item.get("elapsed_sec"),
                "evidence": item.get("evidence"),
            }
            for item in run_data.get("agents", [])
        ],
    }


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Expressive Piano Agent Harness") as demo:
        gr.Markdown(
            """
# Expressive Piano Agent Harness

多智能体无谱钢琴表达分析。系统不会把音频转成乐谱，也不会判断唯一正确答案；它使用多个音频分析 agent 提取证据，再由 LLM 或本地模板生成反思性点评。
"""
        )
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 输入")
                expert_upload = gr.Audio(label="专家录音上传", type="filepath")
                user_upload = gr.Audio(label="学生录音上传", type="filepath")
                expert_text = gr.Textbox(label="专家录音路径", value=str(DEFAULT_EXPERT))
                user_text = gr.Textbox(label="学生录音路径", value=str(DEFAULT_USER))
                max_duration = gr.Slider(0, 240, value=180, step=10, label="最大分析秒数，0=完整")
                segments = gr.Slider(12, 96, value=48, step=4, label="对齐分段数")
                dtw_step = gr.Slider(2, 16, value=6, step=1, label="DTW 抽帧步长，越大越快")
                use_openai = gr.Checkbox(label="调用 OpenAI 综合点评", value=False)
                config_path = gr.Textbox(
                    label="LLM 配置文件路径",
                    value="",
                    info="留空时优先读取 scripts/agent_harness/configs/llm.local.json，不存在则读取 llm.example.json。",
                )
                profile_name = gr.Textbox(
                    label="LLM Profile",
                    value="",
                    info="留空时使用配置文件 default_profile。",
                )
                model = gr.Textbox(
                    label="模型 ID 覆盖",
                    value="",
                    info="留空时使用 profile.models.synthesis。",
                )
                run_btn = gr.Button("运行多智能体分析", variant="primary")
            with gr.Column(scale=2):
                gr.Markdown("## 结果")
                timeline = gr.Markdown(label="Agent 运行过程")
                final_report = gr.Markdown(label="最终点评")

        with gr.Tab("Agent 细节"):
            agents_md = gr.Markdown()
        with gr.Tab("结构化 JSON"):
            metrics_json = gr.Code(language="json")
        with gr.Tab("图表"):
            with gr.Row():
                waveform = gr.Image(label="波形/RMS", type="filepath")
                tempo = gr.Image(label="Tempo/Rubato", type="filepath")
            with gr.Row():
                dynamics = gr.Image(label="Dynamics", type="filepath")
                alignment = gr.Image(label="Alignment Segments", type="filepath")
        with gr.Tab("输出文件"):
            files = gr.Files(label="下载输出文件")

        run_btn.click(
            fn=run_ui,
            inputs=[
                expert_upload,
                user_upload,
                expert_text,
                user_text,
                max_duration,
                segments,
                dtw_step,
                use_openai,
                config_path,
                profile_name,
                model,
            ],
            outputs=[
                timeline,
                final_report,
                agents_md,
                metrics_json,
                waveform,
                tempo,
                dynamics,
                alignment,
                files,
            ],
        )
    return demo


if __name__ == "__main__":
    port_value = os.environ.get("GRADIO_SERVER_PORT", "").strip()
    server_port = int(port_value) if port_value else None
    build_demo().launch(
        server_name="127.0.0.1",
        server_port=server_port,
        show_error=True,
        allowed_paths=[str(ROOT / "files")],
    )
