from __future__ import annotations

from typing import Any

from ..core import AgentResult, HarnessContext, classify_delta, fmt_delta


class SignalOverviewAgent:
    name = "signal_overview"
    title = "全局信号概览 Agent"

    def run(self, context: HarnessContext) -> AgentResult:
        analysis = context.analysis
        expert = analysis["expert"]
        user = analysis["user"]
        comp = analysis["comparison"]
        align = analysis["alignment"]

        duration_delta = comp["duration_delta_sec_user_minus_expert"]
        tempo_delta = comp["estimated_tempo_delta_bpm_user_minus_expert"]
        dyn_delta = comp["dynamic_contrast_delta_db_user_minus_expert"]

        summary = (
            f"学生版本比专家版本短 {abs(duration_delta):.2f}s，整体时长比为 "
            f"{comp['duration_ratio_user_over_expert']:.3f}。"
            f"估计全局 tempo 差异为 {fmt_delta(tempo_delta, ' BPM')}，"
            f"动态对比差异为 {fmt_delta(dyn_delta, ' dB')}。"
            f"chroma 对齐均值 {align['mean_chroma_similarity']:.3f}，质量为 {comp['alignment_quality']}。"
        )

        evidence = {
            "expert_duration_sec": expert["duration_sec"],
            "user_duration_sec": user["duration_sec"],
            "duration_delta_sec": duration_delta,
            "duration_assessment": classify_delta(duration_delta, 2.0, 6.0),
            "tempo_delta_bpm": tempo_delta,
            "dynamic_contrast_delta_db": dyn_delta,
            "alignment": align,
            "limitations": analysis.get("limitations", []),
        }
        return AgentResult(
            name=self.name,
            title=self.title,
            status="ok",
            summary=summary,
            evidence=evidence,
            artifacts=[str(context.analysis_dir / "01_waveform_rms.png")],
        )


class RubatoTimingAgent:
    name = "rubato_timing"
    title = "Rubato 与时间弹性 Agent"

    def run(self, context: HarnessContext) -> AgentResult:
        analysis = context.analysis
        expert = analysis["expert"]
        user = analysis["user"]
        comp = analysis["comparison"]
        delta = comp["rubato_proxy_delta_user_minus_expert"]

        if delta < -8:
            interpretation = "学生的局部速度弹性低于专家，整体更稳定或更少时间弯曲。"
        elif delta > 8:
            interpretation = "学生的局部速度弹性高于专家，整体更自由或更不稳定。"
        else:
            interpretation = "学生与专家的整体 tempo 弹性接近，差异更可能出现在局部位置而非总量。"

        summary = (
            f"rubato proxy：专家 {expert['profile']['rubato_proxy']:.1f}，"
            f"学生 {user['profile']['rubato_proxy']:.1f}，差值 {fmt_delta(delta)}。"
            f"{interpretation}"
        )
        evidence = {
            "expert_tempo_mean_bpm": expert.get("tempo_mean_bpm"),
            "user_tempo_mean_bpm": user.get("tempo_mean_bpm"),
            "expert_tempo_cv": expert.get("tempo_cv"),
            "user_tempo_cv": user.get("tempo_cv"),
            "rubato_proxy_delta": delta,
            "interpretation": interpretation,
        }
        return AgentResult(
            name=self.name,
            title=self.title,
            status="ok",
            summary=summary,
            evidence=evidence,
            artifacts=[str(context.analysis_dir / "02_tempo_curves.png")],
        )


class DynamicsAgent:
    name = "dynamics"
    title = "力度与动态轮廓 Agent"

    def run(self, context: HarnessContext) -> AgentResult:
        analysis = context.analysis
        expert = analysis["expert"]
        user = analysis["user"]
        comp = analysis["comparison"]
        delta = comp["dynamic_contrast_delta_db_user_minus_expert"]

        if delta < -3:
            interpretation = "学生动态范围小于专家，可能更克制，也可能高点与低点区分不足。"
        elif delta > 3:
            interpretation = "学生动态范围大于专家，可能更戏剧化，也可能局部强弱变化过大。"
        else:
            interpretation = "学生与专家的总体动态范围接近，下一步应看曲线形状和位置。"

        summary = (
            f"动态对比：专家 {expert['dynamic_contrast_db']:.2f} dB，"
            f"学生 {user['dynamic_contrast_db']:.2f} dB，差值 {fmt_delta(delta, ' dB')}。"
            f"{interpretation}"
        )
        evidence = {
            "expert_dynamic_contrast_db": expert["dynamic_contrast_db"],
            "user_dynamic_contrast_db": user["dynamic_contrast_db"],
            "dynamic_delta_db": delta,
            "expert_rms_std_db": expert["rms_std_db"],
            "user_rms_std_db": user["rms_std_db"],
            "interpretation": interpretation,
        }
        return AgentResult(
            name=self.name,
            title=self.title,
            status="ok",
            summary=summary,
            evidence=evidence,
            artifacts=[str(context.analysis_dir / "03_dynamic_curves.png")],
        )


class StructureAlignmentAgent:
    name = "structure_alignment"
    title = "结构对齐与回听片段 Agent"

    def run(self, context: HarnessContext) -> AgentResult:
        comp = context.analysis["comparison"]
        segments = comp.get("lowest_similarity_segments", [])
        lines = []
        for row in segments[:5]:
            lines.append(
                f"Segment {int(row['segment'])}: {row['ref_time_start_sec']:.1f}s-"
                f"{row['ref_time_end_sec']:.1f}s，相似度 {row['mean_chroma_similarity']:.3f}，"
                f"动态差 {fmt_delta(row['dynamic_delta_db_user_minus_expert'], ' dB')}"
            )
        summary = "最值得回听的片段：" + "；".join(lines) if lines else "未找到显著片段。"
        evidence = {
            "lowest_similarity_segments": segments,
            "suggested_use": "这些片段适合让学生和专家版本交替回听，判断差异是表达选择还是执行稳定性问题。",
        }
        return AgentResult(
            name=self.name,
            title=self.title,
            status="ok",
            summary=summary,
            evidence=evidence,
            artifacts=[str(context.analysis_dir / "04_alignment_segments.png")],
        )


class ReflectionPromptAgent:
    name = "reflection_prompt"
    title = "反思提示 Agent"

    def run(self, context: HarnessContext) -> AgentResult:
        prompts = context.analysis.get("reflection_prompts", [])
        profile_delta = context.analysis["comparison"].get("profile_delta_user_minus_expert", {})
        summary = "\n".join(f"{idx}. {prompt}" for idx, prompt in enumerate(prompts, 1))
        evidence: dict[str, Any] = {
            "reflection_prompts": prompts,
            "profile_delta_user_minus_expert": profile_delta,
            "pedagogical_stance": "这些提示用于推动学生反思，不作为分数或正确答案。",
        }
        return AgentResult(
            name=self.name,
            title=self.title,
            status="ok",
            summary=summary,
            evidence=evidence,
            artifacts=[str(context.analysis_dir / "05_expressive_radar.png")],
        )
