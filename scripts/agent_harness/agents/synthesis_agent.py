from __future__ import annotations

import json
from typing import Any

from ..config import LlmProfile, load_llm_profile
from ..core import AgentResult, HarnessContext


SYSTEM_PROMPT = """你是一位严谨的钢琴教师与HCI研究型音乐表达分析助手。
你的任务不是判断学生是否弹得“正确”，也不是要求学生复制专家。
你要基于多智能体给出的音频分析证据，外化可听见的表达差异，并把差异转化为学习者可以反思和尝试的练习建议。

必须遵守：
- 不要声称你知道演奏者真实意图。
- 没有乐谱时，不要谈具体小节、和声功能、声部关系或作曲意图。
- 把信号指标解释为可能的表达线索，而不是权威判断。
- 反馈要具体、可操作，并保护学生的个人诠释空间。
"""


def build_user_prompt(context: HarnessContext, prior_results: list[AgentResult]) -> str:
    evidence = [
        {
            "agent": result.name,
            "title": result.title,
            "summary": result.summary,
            "evidence": result.evidence,
        }
        for result in prior_results
    ]
    return f"""请基于以下多智能体分析结果，生成一份中文钢琴学习反馈报告。

专家录音：{context.expert_path}
学生录音：{context.user_path}
分析模式：无谱音频对比，不做音频转乐谱。

输出 Markdown，结构必须包含：

## 总体印象
3-5句话，描述学生与专家的整体表达差异。

## 可观察差异
列出5条。每条包含：可观察现象、可能的表达含义、不确定性。

## 专家表达选择
说明专家版本中值得观察的处理方式，但不要写成唯一标准。

## 学生个人诠释空间
指出学生当前可能已经形成的表达倾向，以及可以保留/发展的位置。

## 下一轮练习建议
给出5条具体练习。每条包含：目标、怎么练、听什么反馈。

## 对系统判断的边界
说明无谱音频分析的限制。

多智能体证据：
```json
{json.dumps(evidence, ensure_ascii=False, indent=2)}
```
"""


class OpenAISynthesisAgent:
    name = "openai_synthesis"
    title = "LLM 综合点评 Agent"

    def __init__(
        self,
        model: str | None = None,
        enabled: bool = True,
        config_path: str | None = None,
        profile_name: str | None = None,
        llm_profile: LlmProfile | None = None,
    ):
        self.model_override = model
        self.enabled = enabled
        self.config_path = config_path
        self.profile_name = profile_name
        self.llm_profile = llm_profile

    def run_with_results(
        self, context: HarnessContext, prior_results: list[AgentResult]
    ) -> AgentResult:
        if not self.enabled:
            return self._fallback(context, prior_results, "OpenAI synthesis disabled.")
        profile = self.llm_profile or load_llm_profile(self.config_path, self.profile_name)
        model = profile.model_for("synthesis", self.model_override)
        if profile.provider != "openai":
            return self._fallback(
                context,
                prior_results,
                f"Unsupported LLM provider '{profile.provider}'. Current client supports OpenAI-compatible APIs.",
                profile=profile,
                model=model,
            )
        if not profile.api_key:
            return self._fallback(
                context,
                prior_results,
                f"API key is not set ({profile.api_key_source}).",
                profile=profile,
                model=model,
            )

        try:
            from openai import OpenAI
        except ModuleNotFoundError:
            return self._fallback(
                context,
                prior_results,
                "openai package is not installed.",
                profile=profile,
                model=model,
            )

        try:
            client = OpenAI(api_key=profile.api_key, base_url=profile.base_url)
            text, api_method = self._call_openai_compatible(
                client=client,
                model=model,
                context=context,
                prior_results=prior_results,
            )
            if not text.strip():
                return self._fallback(
                    context,
                    prior_results,
                    "OpenAI-compatible endpoint returned empty text.",
                    profile=profile,
                    model=model,
                )
            return AgentResult(
                name=self.name,
                title=self.title,
                status="ok",
                summary=text.strip(),
                evidence={
                    **profile.redacted("synthesis", self.model_override),
                    "api_method": api_method,
                },
            )
        except Exception as exc:
            return self._fallback(
                context,
                prior_results,
                f"OpenAI-compatible call failed: {exc}",
                profile=profile,
                model=model,
            )

    def _call_openai_compatible(
        self,
        client: Any,
        model: str,
        context: HarnessContext,
        prior_results: list[AgentResult],
    ) -> tuple[str, str]:
        user_prompt = build_user_prompt(context, prior_results)
        response_error: Exception | None = None
        api_method = (
            self.llm_profile.api_method if self.llm_profile is not None else "auto"
        ).lower()

        if api_method in {"auto", "responses"}:
            try:
                response = client.responses.create(
                    model=model,
                    input=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                text = getattr(response, "output_text", "") or ""
                if text.strip():
                    return text, "responses"
            except Exception as exc:
                response_error = exc
                if api_method == "responses":
                    raise

        if api_method in {"auto", "chat.completions", "chat_completions"}:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            message = completion.choices[0].message
            text = message.content or ""
            if text.strip():
                return text, "chat.completions"
            if response_error:
                raise RuntimeError(
                    f"Responses API failed first: {response_error}; Chat Completions returned empty text."
                )
            raise RuntimeError("Chat Completions returned empty text.")
        raise ValueError(f"Unsupported api_method '{api_method}'. Use auto, responses, or chat.completions.")

    def _fallback(
        self,
        context: HarnessContext,
        prior_results: list[AgentResult],
        reason: str,
        profile: LlmProfile | None = None,
        model: str | None = None,
    ) -> AgentResult:
        attempted_remote = not (
            "disabled" in reason.lower()
            or "api key is not set" in reason.lower()
            or "openai package is not installed" in reason.lower()
        )
        status_line = (
            "系统已尝试调用远程 LLM，但调用失败，因此改用本地模板化反馈。"
            if attempted_remote
            else "系统已完成本地多智能体分析，但没有调用远程 LLM。以下是基于本地 agent 证据生成的模板化反馈。"
        )
        sections = [
            "## 总体印象",
            status_line,
            "",
            f"LLM fallback 原因：`{reason}`",
            "",
            "## Agent 观察摘要",
        ]
        for result in prior_results:
            sections.append(f"### {result.title}")
            sections.append(result.summary)
            sections.append("")
        sections.extend(
            [
                "## 下一轮练习建议",
                "1. 先听专家和学生版本的整体速度推进，判断学生是否希望保留当前更快或更慢的整体倾向。",
                "2. 对照动态曲线，选择两个动态差异明显的片段，分别尝试更克制和更戏剧化的处理。",
                "3. 对照最值得回听的片段，交替播放专家和学生版本，记录差异是否属于个人表达目标。",
                "4. 不要以相似度作为分数，把它当作发现差异位置的索引。",
                "5. 下一次录音前先写一句表达目标，再比较演奏是否实现了这个目标。",
                "",
                "## 对系统判断的边界",
                "当前系统没有乐谱输入，也不做音频转乐谱，因此不能给出小节、和声、声部或真实意图层面的断言。",
            ]
        )
        return AgentResult(
            name=self.name,
            title=self.title,
            status="fallback",
            summary="\n".join(sections),
            evidence={
                "fallback_reason": reason,
                **(
                    profile.redacted("synthesis", self.model_override)
                    if profile
                    else {"model": model or self.model_override or "gpt-4o-mini"}
                ),
            },
        )
