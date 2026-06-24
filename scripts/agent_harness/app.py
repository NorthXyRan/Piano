from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

import gradio as gr
import matplotlib

os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib_cache"))
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False

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
    dashboard_html = build_dashboard_html(run_data)
    segment_rows = build_segment_rows(run_data)
    delta_chart = build_delta_chart(run_data, output_dir)
    gallery = build_gallery_items(artifacts, delta_chart)
    files = [path for path in artifacts.values() if Path(path).exists()]
    if delta_chart and Path(delta_chart).exists():
        files.append(delta_chart)

    return (
        dashboard_html,
        delta_chart,
        segment_rows,
        gallery,
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


def build_dashboard_html(run_data: dict[str, Any]) -> str:
    analysis = run_data.get("agents", [{}])[0].get("evidence", {})
    options = run_data.get("options", {})
    llm = options.get("llm", {})
    alignment = analysis.get("alignment", {})
    cards = [
        (
            "整体时长差",
            f"{analysis.get('duration_delta_sec', 0):+.2f}s",
            "学生 - 专家，接近 0 表示整体长度相近",
        ),
        (
            "Tempo 差异",
            f"{analysis.get('tempo_delta_bpm', 0):+.2f} BPM",
            "当前是全局估计，局部 rubato 需看曲线",
        ),
        (
            "动态对比差",
            f"{analysis.get('dynamic_contrast_delta_db', 0):+.2f} dB",
            "正值表示学生整体动态范围更大",
        ),
        (
            "对齐相似度",
            f"{alignment.get('mean_chroma_similarity', 0):.3f}",
            f"质量：{analysis.get('alignment', {}).get('quality', options.get('alignment_quality', '见 JSON'))}",
        ),
        (
            "LLM 状态",
            "启用" if options.get("use_openai") else "未启用",
            f"{llm.get('profile', 'n/a')} / {llm.get('model', 'n/a')}",
        ),
    ]
    card_html = "".join(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-note">{note}</div>
        </div>
        """
        for label, value, note in cards
    )
    return f"""
    <div class="dashboard-wrap">
      <div class="dashboard-title">演奏差异总览</div>
      <div class="dashboard-subtitle">这些指标不是分数，而是帮助定位“值得回听的位置”和“可讨论的表达差异”。</div>
      <div class="metric-grid">{card_html}</div>
    </div>
    """


def build_segment_rows(run_data: dict[str, Any]) -> list[list[Any]]:
    segments = run_data.get("analysis", {}).get("comparison", {}).get("lowest_similarity_segments", [])
    rows = []
    for item in segments:
        rows.append(
            [
                int(item.get("segment", 0)),
                f"{item.get('ref_time_start_sec', 0):.1f}-{item.get('ref_time_end_sec', 0):.1f}s",
                round(float(item.get("mean_chroma_similarity", 0)), 3),
                round(float(item.get("dynamic_delta_db_user_minus_expert", 0)), 2),
                round(float(item.get("onset_strength_delta_user_minus_expert", 0)), 3),
                "优先回听" if float(item.get("mean_chroma_similarity", 1)) < 0.86 else "可抽查",
            ]
        )
    return rows


def build_delta_chart(run_data: dict[str, Any], output_dir: Path) -> str:
    comparison = run_data.get("analysis", {}).get("comparison", {})
    values = {
        "Rubato": comparison.get("rubato_proxy_delta_user_minus_expert", 0),
        "动态范围": comparison.get("dynamic_contrast_delta_db_user_minus_expert", 0),
        "呼吸空间": comparison.get("breathing_space_delta_user_minus_expert", 0),
        "触键清晰": comparison.get("onset_clarity_delta_user_minus_expert", 0),
        "音色亮度": comparison.get("brightness_delta_user_minus_expert", 0),
    }
    fig, ax = plt.subplots(figsize=(9, 3.8))
    names = list(values.keys())
    vals = [float(v or 0) for v in values.values()]
    colors = ["#2f6f73" if value >= 0 else "#b65f2a" for value in vals]
    ax.barh(names, vals, color=colors)
    ax.axvline(0, color="#222222", linewidth=1)
    ax.set_title("学生相对专家的表达特征差异", fontsize=14, pad=12)
    ax.set_xlabel("学生 - 专家")
    ax.grid(axis="x", alpha=0.22)
    for idx, value in enumerate(vals):
        ax.text(value, idx, f" {value:+.2f}", va="center", fontsize=10)
    fig.tight_layout()
    path = output_dir / "dashboard_expression_delta.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return str(path)


def build_gallery_items(artifacts: dict[str, str], delta_chart: str) -> list[str]:
    ordered = [
        delta_chart,
        artifacts.get("05_expressive_radar.png", ""),
        artifacts.get("01_waveform_rms.png", ""),
        artifacts.get("02_tempo_curves.png", ""),
        artifacts.get("03_dynamic_curves.png", ""),
        artifacts.get("04_alignment_segments.png", ""),
    ]
    return [path for path in ordered if path and Path(path).exists()]


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
    css = """
    .dashboard-wrap {
      padding: 18px;
      border-radius: 18px;
      background: linear-gradient(135deg, #f4efe4 0%, #e9f0ec 55%, #f8f2e8 100%);
      border: 1px solid #d7cab8;
    }
    .dashboard-title { font-size: 24px; font-weight: 800; color: #243832; }
    .dashboard-subtitle { margin-top: 4px; color: #5e625a; }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .metric-card {
      padding: 14px;
      border-radius: 14px;
      background: rgba(255,255,255,0.72);
      box-shadow: 0 8px 24px rgba(47, 65, 55, 0.08);
    }
    .metric-label { color: #667066; font-size: 13px; }
    .metric-value { color: #1d302b; font-size: 26px; font-weight: 800; margin-top: 4px; }
    .metric-note { color: #6f766e; font-size: 12px; margin-top: 6px; line-height: 1.35; }
    """
    with gr.Blocks(title="Expressive Piano Agent Harness", css=css) as demo:
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
                dashboard = gr.HTML()
                with gr.Row():
                    delta_chart_img = gr.Image(label="表达特征差异", type="filepath")
                segment_table = gr.Dataframe(
                    headers=["片段", "时间", "音高轮廓相似度", "动态差 dB", "起音差", "建议"],
                    label="优先回听片段",
                    interactive=False,
                )
                final_report = gr.Markdown(label="最终点评")

        with gr.Tab("可视化画廊"):
            gallery = gr.Gallery(label="分析图表", columns=2, height="auto", object_fit="contain")
        with gr.Tab("Agent 过程"):
            timeline = gr.Markdown(label="Agent 运行过程")
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
                dashboard,
                delta_chart_img,
                segment_table,
                gallery,
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
