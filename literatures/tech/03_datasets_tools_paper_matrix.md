# Datasets, Tools, and Paper Matrix

## 1. 数据集

| 名称 | 内容 | 对项目的价值 | 来源 |
|---|---|---|---|
| MAESTRO | 172+ 小时高水平钢琴 audio-MIDI，同步精度约 3 ms | AMT、performance modeling 的基础数据 | https://arxiv.org/abs/1810.12247 |
| Batik-plays-Mozart | Mozart sonatas，专家 MIDI/audio，note-level score alignment，harmony/cadence/phrase annotations | 最贴近“表达 + 乐句/和声解释”的数据范式 | https://arxiv.org/abs/2309.02399 |
| Con Espressione Game | 多位名家演奏片段 + 自由文本 expressive character 描述 + tempo/dynamics curves | 支撑“表达性格/语言描述”而非单纯打分 | https://arxiv.org/abs/2008.02194 |
| ASAP | 222 scores, 1068 performances, beat-level alignment | 大规模 score-performance 对齐训练/评估 | Batik paper 中综述；可从相关项目页继续追踪 |
| Vienna 4x22 | 4 个片段，每个 22 个演奏，note-level alignment | 多版本专家/学生表达比较 | Batik paper 中综述 |
| CrestMuse PEDB | 35 pieces, 411 performances, note-level alignment, phrase info | phrase-level 表达研究 | Batik paper 中综述 |
| MazurkaBL | 44 Chopin Mazurkas, 2000 recordings 的 beat/loudness/expressive markings | Chopin rubato/dynamics 对比非常相关 | Batik paper 中综述 |
| PianoCoRe | 250,046 performances, 5,625 pieces；PianoCoRe-A 有 note-aligned subset | 2026 年大规模 expressive piano MIDI 数据参考 | https://arxiv.org/abs/2605.06627 |
| PianoVAM | amateur practice: video/audio/MIDI/hand landmarks/fingering | 若未来加入手型/指法/练习行为，很有参考价值 | https://arxiv.org/abs/2509.08800 |

## 2. 模型与工具

| 工具/模型 | 类型 | 能做什么 | 项目用法 | 来源 |
|---|---|---|---|---|
| Onsets and Frames | piano AMT | solo piano audio -> pitch/onset/offset/velocity | 学生音频转 note events | https://arxiv.org/abs/1710.11153 |
| Basic Pitch | lightweight AMT | audio -> MIDI/note events，跨乐器 | 快速原型，CLI/Python 方便 | https://github.com/spotify/basic-pitch |
| MT3 | Transformer AMT | multi-task/multitrack transcription | 作为高级转录基线 | https://arxiv.org/abs/2111.03017 |
| Partitura | symbolic music Python package | 读 score/MIDI/alignment，voice separation | score parsing + feature extraction | https://arxiv.org/abs/2206.01071 |
| Matchmaker | score following/alignment | real-time piano score following | 实时/交互式对齐基础 | https://arxiv.org/abs/2510.10087 |
| madmom | MIR library | onset/beat/downbeat/tempo/piano transcription | 音频特征基线工具 | https://arxiv.org/abs/1605.07008 |
| librosa | audio analysis library | CQT/chroma/DTW/onset/loudness pipeline | 自定义无谱对齐和特征 | https://librosa.org/ |
| music21 | computational musicology toolkit | score analysis, harmony, key, phrase support | score-side music concept extraction | https://web.mit.edu/music21/ |

## 3. 论文矩阵

| 论文 | 解决的问题 | 可复用部分 | 局限 |
|---|---|---|---|
| Onsets and Frames | polyphonic piano transcription | note events + velocity | 真实录音泛化和 pedal/offset 仍可能出错 |
| MAESTRO | high-quality audio-MIDI dataset | 训练/评估 AMT 与 expressive modeling | 不直接提供 score-level phrase/harmony annotations |
| Basic Pitch | lightweight instrument-agnostic AMT | 快速部署、note events CSV | 对 solo piano 专门优化程度不如 piano-specific 模型 |
| MT3 | unified sequence-to-sequence AMT | Transformer 转录范式 | 工程复杂度高，训练不便 |
| Partitura | symbolic score/performance processing | note arrays, alignments, voice separation | 主要处理 symbolic，不直接解决 audio AMT |
| Matchmaker | real-time score following | interactive alignment | 2025 新工具，工程成熟度需实测 |
| Con Espressione Game | expressive character 描述数据 | 表达语言、维度、prompt 设计 | 数据规模较小，解释非确定性 |
| Mid-level perceptual features for piano emotion | perceived emotion/arousal/valence | 情感/表达性格的中间特征 | 不能直接等同“演奏意图” |
| Tonal tension and expressive performance | score tension -> tempo/dynamics | 和声/张力解释 | 需要 score/harmony context |
| Score-informed Networks for MPA | score-aware performance assessment | 基础 performance quality 评估 | 与 expressive exploration 的教育目标不同 |

## 4. 推荐阅读顺序

1. 先读 Onsets and Frames、Basic Pitch、MAESTRO，确认 audio-to-note 的可行性与误差来源。
2. 再读 Partitura、Matchmaker、audio-to-score alignment，确认如何把演奏映射到 score positions。
3. 再读 Batik-plays-Mozart、Con Espressione Game、mid-level perceptual features，建立 expressive explanation 的理论基础。
4. 最后读 Score-informed MPA，把它作为对照：你的系统不是传统评分系统。

## 5. 可直接转成原型任务的 backlog

| 优先级 | 任务 | 验收标准 |
|---|---|---|
| P0 | 读取 MusicXML + student audio | 能显示 score notes 与 transcribed notes |
| P0 | Audio-to-MIDI | 输出 pitch/onset/offset/velocity CSV |
| P0 | Score-performance alignment | 每个 score note 有 matched performance note/confidence |
| P0 | Tempo/dynamics curves | 同一乐句能叠加专家/学生曲线 |
| P1 | Phrase-level radar profile | 每个 phrase 输出 rubato/dynamic/articulation 指标 |
| P1 | Expert comparison | 能比较 2-3 个专家版本 |
| P1 | Reflection prompt generator | 基于 measured features 生成 non-authoritative prompts |
| P2 | Melody/accompaniment balance | 需要 voice separation 或人工 melody 标注 |
| P2 | Pedal analysis | 有 MIDI pedal CC 时再做 |
| P2 | Emotion descriptor | 只作为 expressive character，不作为准确情感判定 |

## 6. 版权与数据注意事项

- 公开数据集可用于研究，但具体 license 需逐个确认。
- 大师商业录音通常不能直接上传到公开系统分发。
- 原型阶段可以只保存 derived features，不保存或传播原始音频。
- 用户录音涉及隐私，应明确告知保存范围、用途、删除机制。
