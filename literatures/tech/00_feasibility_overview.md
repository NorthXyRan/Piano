# Piano Expressive Exploration: 技术可行性与文献总览

更新时间：2026-06-22

## 结论先行

项目可行，但应该把技术目标分成两层：

- 高可行：音高、节奏、局部速度曲线、rubato、力度/动态范围、articulation、旋律突出度、与多位专家演奏的差异可视化。
- 中等可行：phrase breathing、乐句级动态走向、旋律/伴奏平衡、目标表达轮廓与学生演奏之间的匹配。
- 低可行/需谨慎表述：自动判断“感情是否准确”、自动解释“大师为什么这样弹”。更稳妥的设计是输出 possible interpretations 和 reflection prompts，而不是权威结论。

最推荐的 MVP 是“有谱模式”：输入 MusicXML/MIDI score、专家音频或 MIDI、学生音频；系统先做转录与对齐，再计算音符级和乐句级特征。纯音频无谱模式可作为低门槛入口，但只能可靠支持基础 timing/dynamics/rubato 对比，难以解释和声、乐句、结构。

## 为什么这个方向成立

你的项目不是传统的 Detect -> Correct，而是把专家演奏中的 expressive choices 外化为可比较、可反思的表示。现有 MIR 和 expressive performance research 已经能支撑底层信号处理，但“把差异转化为学生反思”仍是研究创新点。

相关研究给出三条直接支撑：

- Automatic Music Transcription 已能从钢琴音频恢复 pitch/onset/offset/velocity 等 note events。Onsets and Frames 明确将 solo piano audio 转成 MIDI，并预测相对 velocity；Basic Pitch 提供可安装工具；MT3 提供通用 Transformer 转录方向。
- Score-performance alignment 已是成熟任务。Matchmaker、DTW、audio-to-score alignment、Partitura 等工具/论文可把学生演奏、专家演奏和乐谱位置绑定起来。
- Expressive performance research 已长期研究 tempo、dynamics、articulation、tonal tension、expectancy、mid-level perceptual features 与 perceived emotion/expressive character 的关系。

## 推荐系统架构

```text
Audio / MIDI / Score
        |
        v
Preprocess: trim, denoise, loudness normalization
        |
        v
AMT or MIDI ingest: pitch, onset, offset, velocity, pedal if available
        |
        v
Alignment: student <-> score, expert <-> score, or student <-> expert
        |
        v
Feature extraction: timing, dynamics, articulation, melody balance, phrase
        |
        v
Representation: curves, phrase cards, radar profile, comparison overlays
        |
        v
Reflection prompt: possible interpretations + user goal setting
```

## 对你提出的维度逐项判断

| 维度 | 技术可行性 | 可用信号/特征 | 推荐输出方式 | 风险 |
|---|---:|---|---|---|
| 音高准确性 | 高 | note pitch, missing/extra notes, wrong notes | 明确反馈 | AMT 对真实录音有漏音/假阳性 |
| 节奏准确性 | 高 | onset deviation, IOI ratio, beat-level alignment | 明确反馈 + 曲线 | rubato 不应被误判为错误 |
| rubato | 高 | local tempo curve, beat duration, phrase boundary slowing | 作为表达选择比较 | 需要对齐到 score/beat |
| 响度/力度 | 中-高 | MIDI velocity, audio loudness, note intensity estimate | 动态曲线/contrast | 麦克风距离和音色会影响 loudness |
| articulation | 中 | performed duration / score duration, note overlap ratio | legato/staccato heatmap | 踏板会干扰 offset 判断 |
| phrase breathing | 中 | phrase boundary ritardando, pause, tempo curvature | possible interpretation | 需要乐句标注或自动 phrase detection |
| melodic prominence | 中 | melody voice velocity/loudness vs accompaniment | balance curve | 需要 voice/melody identification |
| 情感/感情 | 低-中 | mid-level perceptual features, arousal/valence, descriptors | 只做“可能的表达性格” | 不能声称准确识别意图 |
| 大师意图解释 | 低 | tempo/dynamics + score structure + LLM/rules | possible interpretations | 解释容易过度权威 |

## MVP 技术建议

### MVP 1：有谱、离线、乐句级对比

目标：做一个可靠的 research prototype，而不是一开始追求全自动音乐老师。

输入：

- MusicXML 或 MIDI score
- 2-3 位专家演奏，优先 MIDI/Disklavier，其次高质量音频
- 学生录音

输出：

- 局部 tempo/rubato 曲线
- dynamics curve
- articulation/legato 指标
- melody-accompaniment balance
- phrase cards：每句显示专家 A/B/学生的处理差异
- reflection prompts：例如“这里 A 明显在 phrase ending 前放慢，可能是在制造呼吸或强调终止。你更想接近哪种处理？”

### MVP 2：无谱、音频到音频对比

输入：学生音频 + 专家音频。

能做：

- 全局 tempo/rubato 对齐
- 粗略 loudness/dynamics 对比
- 基础 note density、onset pattern、音区分布

不建议做：

- 乐句解释
- 和声转折解释
- 准确 melodic prominence
- “第 N 小节”级反馈

## 关键技术依赖

| 模块 | 首选方案 | 备选方案 |
|---|---|---|
| Audio-to-MIDI | Onsets and Frames / Basic Pitch / MT3 | madmom piano transcription, commercial transcription tools |
| Score parsing | Partitura, music21 | pretty_midi, mido |
| Alignment | Matchmaker, DTW, audio-to-score alignment | librosa DTW, custom symbolic alignment |
| Feature extraction | custom note-level feature pipeline | Partitura note arrays + numpy/pandas |
| Emotion/expressive descriptor | mid-level perceptual features, Con Espressione-style descriptors | LLM-generated interpretation constrained by measured features |
| Visualization | phrase-level curves + radar profile | piano-roll heatmap, tempo/dynamics overlay |

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| AMT 错误会污染后续分析 | 高 | 有谱模式下用 score-constrained alignment；允许人工修正；优先 MIDI 专家数据 |
| loudness 不等于 MIDI velocity | 中 | 做录音 loudness normalization；同一环境录制学生；用相对动态而非绝对响度 |
| pedal 影响 note offset/articulation | 中 | 初版弱化 pedal 分析；有 MIDI 时用 pedal CC；音频中只做谨慎估计 |
| “情感识别”过度承诺 | 高 | 输出 expressive character / arousal-valence / possible interpretation，不说准确读心 |
| 大师录音版权 | 高 | 原型用公开数据集、自己录制、或只存特征不分发音频 |
| 多位大师版本缺少对齐 score | 中 | 先选择数据集已有对齐的曲目；后续再扩展 |

## 研究创新点

底层音频分析不是最大的创新，已有工作足够多。你的创新应放在：

- 把 interpretative disagreement 设计成学习资源，而非误差。
- 从 similarity score 转向 expressive profile 和 reflective prompts。
- 把 signal-level differences 翻译成 music concept，但明确保持为 possible interpretations。
- 支持学生设定“目标表达轮廓”，再反馈 Intent -> Performance 的闭环。

## 优先阅读文献

1. Hawthorne et al. (2017/2018), Onsets and Frames: Dual-Objective Piano Transcription. https://arxiv.org/abs/1710.11153
2. Hawthorne et al. (2018/2019), MAESTRO dataset. https://arxiv.org/abs/1810.12247
3. Bittner et al. (2022), Basic Pitch / Lightweight Instrument-Agnostic AMT. https://arxiv.org/abs/2203.09893
4. Gardner et al. (2021/2022), MT3. https://arxiv.org/abs/2111.03017
5. Cancino-Chacon et al. (2020), Con Espressione Game. https://arxiv.org/abs/2008.02194
6. Chowdhury & Widmer (2021), Mid-level perceptual features for expressive piano emotion. https://arxiv.org/abs/2107.13231
7. Hu & Widmer (2023), Batik-plays-Mozart Corpus. https://arxiv.org/abs/2309.02399
8. Park et al. (2025), Matchmaker score following. https://arxiv.org/abs/2510.10087
9. Cancino-Chacon & Grachten (2018), tonal tension and expressive piano performance. https://arxiv.org/abs/1807.01080
10. Huang et al. (2020), Score-informed Networks for Music Performance Assessment. https://arxiv.org/abs/2008.00203
