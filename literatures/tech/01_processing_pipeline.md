# Audio Processing Pipeline for Piano Performance Reflection

## 目标

把学生/专家钢琴演奏从 raw audio 转成可解释的音乐表示：pitch、onset、offset、velocity、tempo curve、dynamics curve、articulation、phrase-level expressive profile。

## 1. 输入类型

### 最稳输入

- Score: MusicXML/MIDI
- Expert performance: MIDI 或与 score 对齐过的 audio/MIDI
- Student performance: WAV/FLAC/M4A audio

### 可接受输入

- Expert audio + student audio，无 score

### 不推荐作为初版唯一输入

- 低质量手机录音 + 无谱 + 想分析乐句/和声/旋律平衡

## 2. 预处理

建议步骤：

- Convert to mono, fixed sample rate, e.g. 22050 Hz or 44100 Hz。
- Trim leading/trailing silence。
- Loudness normalization。PianoVAM 也强调录音条件会影响 loudness，因此做 loudness normalization 有必要。
- Optional denoise/reverb estimation。注意不要过度降噪，否则会破坏 onset 和 decay。

## 3. Audio-to-MIDI / Automatic Music Transcription

### Onsets and Frames

适合：solo piano audio -> MIDI/note events。

关键点：

- 通过 onset detector + frame detector 共同预测音符。
- 输出 pitch, onset, offset，并扩展到 velocity。
- 官方 Magenta 页面说明它能把 solo piano recordings 转成 MIDI，并使用 CNN/LSTM 预测 onset 后约束 frame predictions。

来源：

- Paper: https://arxiv.org/abs/1710.11153
- Magenta page: https://magenta.tensorflow.org/onsets-frames

### Basic Pitch

适合：快速工程原型、跨乐器、安装简单。

关键点：

- `pip install basic-pitch`。
- 输出 MIDI、raw model outputs、note events CSV。
- 支持 polyphonic outputs 和 pitch bend；但项目说明也指出 best on one instrument at a time。

来源：

- Paper: https://arxiv.org/abs/2203.09893
- GitHub: https://github.com/spotify/basic-pitch

### MT3

适合：Transformer-based AMT、多乐器或需要更通用模型时参考。

关键点：

- sequence-to-sequence Transformer。
- 论文强调 preservation of fine-scale pitch and timing。
- GitHub 提供 pretrained checkpoint 和 Colab。

来源：

- Paper: https://arxiv.org/abs/2111.03017
- GitHub: https://github.com/magenta/mt3

## 4. Alignment

### 有谱模式

目标：把每个 performed note 对齐到 score note 或 score beat。

推荐：

- Matchmaker：real-time score following/open-source Python library。
- Partitura：读 MusicXML/MEI/Kern/MIDI，处理 score-performance alignments。
- 如果只做离线原型，也可以先用 DTW + score-constrained symbolic matching 实现，不必一开始追求实时 score following。

来源：

- Matchmaker: https://arxiv.org/abs/2510.10087
- Partitura: https://arxiv.org/abs/2206.01071

### 无谱模式

目标：把学生音频时间轴 warp 到专家音频时间轴。

推荐：

- chroma/CQT features + DTW
- onset strength envelope + DTW
- beat-synchronous features

限制：

- 无法可靠知道“第几小节第几个音”。
- 无法区分 rubato 是表达选择还是节奏错误。
- 无法稳定解释和声转折、phrase boundary、melody-accompaniment balance。

## 5. Feature Extraction

### Note-level features

| Feature | Formula / method | 用途 |
|---|---|---|
| pitch correctness | aligned score pitch vs performed pitch | 音高准确性 |
| onset deviation | performed onset - expected onset | 节奏准确性 |
| IOI ratio | performed IOI / score IOI | 局部节奏伸缩 |
| duration ratio | performed duration / score duration | articulation |
| velocity/loudness | MIDI velocity or estimated note intensity | dynamics |
| missing/extra notes | unmatched score/performance notes | 基础纠错 |

### Beat/phrase-level features

| Feature | Method | 映射到音乐概念 |
|---|---|---|
| local tempo | beat duration -> BPM | tempo/rubato curve |
| rubato index | std/peak-to-peak of local tempo deviation | rubato 强弱 |
| phrase-final ritardando | phrase end 前 tempo slope | phrase breathing |
| pause/breath length | inter-phrase gap | breathing/resting |
| dynamic contrast | velocity/loudness range per phrase | dynamic contrast |
| crescendo slope | regression of dynamics over phrase | phrase shaping |
| articulation profile | duration ratio distribution | legato/staccato tendency |
| melody prominence | melody voice velocity / accompaniment velocity | melodic prominence |

## 6. 从 Signal 到 Music Concept

不要直接从一个数字跳到结论。建议使用中间层：

```text
Measured signal
  -> extracted feature
  -> comparative pattern
  -> possible music concept
  -> reflection prompt
```

例子：

```text
Measured: phrase ending 前 1.8 秒 tempo 从 92 BPM 降到 68 BPM
Feature: phrase-final ritardando = high
Pattern: Expert A 比 Expert B 慢得更多，学生几乎没有放慢
Possible concept: breathing / cadence emphasis / expectation building
Prompt: 你希望这里更像呼吸，还是更保持结构推进？
```

## 7. 数据结构建议

每次分析后保存为 JSON/Parquet：

```json
{
  "piece_id": "chopin_opXX_noY",
  "performance_id": "student_001_take_003",
  "notes": [
    {
      "score_note_id": "m23_n04",
      "pitch": 64,
      "score_onset_beat": 92.0,
      "perf_onset_sec": 143.28,
      "perf_offset_sec": 143.91,
      "velocity": 74,
      "voice": "melody",
      "alignment_confidence": 0.91
    }
  ],
  "phrases": [
    {
      "phrase_id": "p12",
      "rubato_index": 0.63,
      "dynamic_contrast": 0.48,
      "melody_prominence": 0.71,
      "phrase_breathing": 0.59
    }
  ]
}
```

## 8. 工程落地顺序

1. 支持 MIDI 专家 + MusicXML score + 学生 audio。
2. 用 Basic Pitch 或 Onsets and Frames 把学生 audio 转成 note events。
3. 用 score-constrained alignment 对齐。
4. 先做 tempo/dynamics/articulation 三条曲线。
5. 再做 phrase cards 和 radar profile。
6. 最后加入 LLM/规则生成 possible interpretations。

## 9. 需要避免的错误设计

- 不要把 rubato 当作 timing error。
- 不要直接说“你的感情不对”。
- 不要输出单一 similarity score 作为核心反馈。
- 不要在 AMT 置信度低时给小节级精细建议。
- 不要把 loudness 绝对值和 expressive dynamics 混为一谈。
