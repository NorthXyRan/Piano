# Expressive Feature Extraction and Models

## 核心观点

表达性演奏分析不应只提取“错误”，而应提取“选择”：同一 score position 上，不同专家如何处理 timing、dynamics、articulation、phrase、melody balance。学生演奏可以被放在这些选择构成的 expressive space 中。

## 1. Tempo / Rubato

### 可提取内容

- beat-level tempo curve
- local tempo deviation
- phrase-final slowing
- agogic accent：某些重要音符被延长或提前/延后
- rubato density：单位乐句内 tempo 波动的强弱

### 相关工作

Cancino-Chacon, Grachten, Sears, Widmer 使用 expectancy features 和 Basis-Function modeling 预测 expressive tempo/dynamics，说明听觉期待与 tempo 表达之间存在可建模关系。

- What were you expecting? Using Expectancy Features to Predict Expressive Performances of Classical Piano Music: https://arxiv.org/abs/1709.03629

Cancino-Chacon & Grachten 进一步研究 tonal tension 对 expressive tempo/dynamics 的预测作用，发现 tonal tension 对 dynamics 变化预测尤其有帮助。

- A Computational Study of the Role of Tonal Tension in Expressive Piano Performance: https://arxiv.org/abs/1807.01080

### 项目映射

用于解释：

- “这里明显放慢”
- “这里保持推进”
- “这里通过 tempo 弯曲制造呼吸感/期待感”

注意：这些应作为 possible interpretations。

## 2. Dynamics / Loudness

### 可提取内容

- per-note velocity，若有 MIDI/Disklavier 数据最稳
- audio loudness envelope，若只有音频
- phrase dynamic range
- crescendo/decrescendo slope
- melody vs accompaniment dynamic balance

### 相关工作

Onsets and Frames 将 velocity 纳入转录，指出 velocity 对描述钢琴演奏 expressivity 很重要。

- Onsets and Frames: https://arxiv.org/abs/1710.11153

PianoVAM 对录音响度做 normalization，说明真实录音条件会影响 loudness 与 velocity 的一致性。

- PianoVAM: https://arxiv.org/abs/2509.08800

### 项目映射

用于输出：

- dynamic contrast: low/mid/high
- phrase shaping: flat / crescendo / arch-shaped
- melody prominence: melody louder than accompaniment or not

## 3. Articulation

### 可提取内容

- duration ratio = performed duration / notated duration
- note overlap ratio
- inter-note gap
- staccato/legato tendency

### 风险

踏板会让音频 offset 变得模糊。若有 MIDI sustain pedal CC，articulation 更可靠；若只有音频，应谨慎表述为 perceived articulation 或 decay-based estimate。

## 4. Phrase Breathing

### 可提取内容

- phrase boundary 前后的 tempo slope
- phrase ending pause/gap
- phrase-start pickup timing
- dynamic tapering at cadence

### 所需条件

- 最好有 phrase annotations。
- Batik-plays-Mozart 把 score、note-level performance alignment、harmony/cadence/phrase annotations 连起来，是该方向非常相关的数据参照。

来源：

- Batik-plays-Mozart Corpus: https://arxiv.org/abs/2309.02399

### 项目映射

可视化为 phrase cards：

```text
Phrase 12:
Expert A: high phrase-final ritardando + soft landing
Expert B: stable tempo + strong cadence
Student: stable tempo + weak dynamic taper
Possible prompt: 你希望这里更像“呼吸”，还是更像“结构性结束”？
```

## 5. Melody Prominence / Balance

### 可提取内容

- melody voice velocity/loudness vs accompaniment voice velocity/loudness
- top voice salience
- left/right hand balance if hand separation available
- melody note onset emphasis

### 工具支撑

Partitura 可处理 symbolic scores、note arrays、alignments，并包含 voice separation 工具。

- Partitura: https://arxiv.org/abs/2206.01071

PianoVAM 提供 audio/MIDI/video/hand landmarks/fingering，可以作为未来左手/右手、手指、动作维度的参考。

- PianoVAM: https://arxiv.org/abs/2509.08800

## 6. Emotion / Expressive Character

### 推荐表述

不要说“系统识别出你弹得悲伤/激情不够”。建议说：

- “这个演奏在模型特征上更接近 high arousal / strong contrast / flowing rubato。”
- “听众描述中，这类特征常与 dramatic / singing / calm 等词相关。”
- “这不是判定，而是供你反思的描述维度。”

### 相关工作

Con Espressione Game 收集了 45 个古典钢琴演奏片段的约 1500 条自由文本表达性格描述，并把 tempo/dynamics curves 等特征与描述维度联系起来。

- Con Espressione Game: https://arxiv.org/abs/2008.02194

Chowdhury & Widmer 发现 mid-level perceptual features 对区分同一作品不同钢琴家演奏中的 arousal/valence 有贡献，甚至优于预训练 emotion model。

- On Perceived Emotion in Expressive Piano Performance: https://arxiv.org/abs/2107.13231

后续工作还探索了 expressive performance retrieval：用 expressive character 或 emotion 描述检索对应演奏。

- Expressivity-aware Music Performance Retrieval: https://arxiv.org/abs/2401.14826

## 7. Automatic Performance Assessment

Huang et al. 提出 score-informed networks for music performance assessment，把 aligned pitch contours 和 score 一起输入模型预测 assessment ratings。这类工作可支撑“评分/评估”模块，但与你的项目目标不同：它更适合判断 performance quality，不适合直接支持 expressive identity。

来源：

- Score-informed Networks for Music Performance Assessment: https://arxiv.org/abs/2008.00203

项目建议：

- 不把 MPA 模型作为主线。
- 可以把它作为 supplementary diagnostic，用于基础 pitch/rhythm correctness。
- 对表达性反馈仍使用 comparative profile + reflection prompt。

## 8. 可视化建议

### 适合的图

- tempo/rubato curve overlay：专家 A/B/学生同一乐句叠加。
- dynamics curve overlay：显示力度轮廓。
- phrase card：每句的表达选择摘要。
- radar profile：rubato、phrase breathing、dynamic contrast、melody prominence、articulation。
- piano-roll heatmap：显示学生和专家在 note-level 的 timing/dynamics 差异。

### 不建议的图

- 单一 similarity score。
- 红绿错误热图覆盖所有表达维度。
- “情感准确率”仪表盘。

## 9. 解释生成策略

### 规则模板

```text
If phrase-final ritardando high AND dynamic taper high:
  possible concepts = [breathing, cadence emphasis, singing phrasing]

If tonal tension high AND dynamics increase:
  possible concepts = [tension building, harmonic emphasis]

If melody_prominence high AND accompaniment stable:
  possible concepts = [singing line, melodic foregrounding]
```

### LLM 使用边界

LLM 可以生成自然语言解释，但必须由 measured features 约束：

- 输入：score context + feature differences + confidence。
- 输出：2-3 个 possible interpretations。
- 禁止输出：确定性心理状态，例如“大师想表达悲伤”。

推荐文案：

```text
系统观察到：A 在这句结尾有更明显的放慢和减弱。
这可能对应几种音乐理解：呼吸感、终止强调、期待感。
你更认同哪一种？如果是你，会保留这种处理吗？
```
