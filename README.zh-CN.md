# feel-bench（手感试验台）

[English](README.md) | **简体中文**

> 像做台架测试一样调游戏手感：用格子和秒把手感写下来，按真实物理帧率验证，用跳跃检查关卡里每一道坑，用手机摄像头测延迟，让盲测 A/B 决定什么叫“更好”。

## 这是什么

`feel-bench` 是一个面向游戏开发者的智能体技能，帮助你把操作手感调对，并且一直保持正确。当有人说跳跃“飘”、镜头“发涩”、打击“没感觉”时，智能体不会去瞎猜重力。它先写一份简短的简报，把形容词翻译成杠杆，把所有数值放进一份手感规格（`feel.json`），再运行一个只用标准库的辅助工具，逐帧展示引擎实际会怎么做。然后它用新跳跃检查关卡、测量运行中的版本，并在任何人说“现在更好了”之前，先做一次盲测并用精确符号检验计票。

### 要解决的问题

调手感通常是这样一个循环：改一个数，玩十秒，说“好多了”。这个循环有几种常见的失败方式：

- 课本上的跳跃公式，与逐帧模拟出的最高点相差好几个百分点；
- 0.01 秒的土狼时间不到一帧，等于没有；
- 每帧 `lerp(a, b, 0.1)` 在 30 fps 下慢一倍；
- 跳跃变短后，一个坑悄悄变得跳不过去；
- 110 毫秒的输入延迟，从来没人测过；
- 一个“明显改进”，盲测玩家却分不出来。

feel-bench 把这些都变成每次改动前后都要跑的检查。

## 功能

- **手感简报 -> 杠杆。** 三个词、一个禁用词、原话抱怨、先调的那一个动作，通过“词—杠杆”对照表映射到具体参数。
- **一份手感规格。** 跳跃、跑动、宽容窗口、带设计意图的坑、反馈分级、无障碍开关，都写在一个 JSON 文件里，单位是格子和秒。
- **逐帧模拟。** 按工程真实物理帧率做半隐式欧拉积分：逐帧最高点、到顶帧、滞空时间、最短点按跳，以及能精确达到目标高度的起跳速度。
- **关卡距离检查。** 每个坑和台阶得到 `CLEAR`、`TIGHT`、`IMPOSSIBLE` 或 `TOO HIGH`，任何结论违背设计意图时命令失败。
- **宽容窗口换算成帧。** 土狼时间、跳跃预输入等换算为整数帧，对零帧窗口和严重取整给出警告。
- **与帧率无关的平滑。** 把每帧 lerp 常数换算为指数平滑速率，在 30、60、144 fps 下保持当前手感。
- **视频测延迟。** 慢动作视频帧数 -> 中位数、p90，以及考虑相机一帧误差的结论。
- **真正的盲测 A/B。** 精确双侧符号检验、最小样本警告，以及明确的“没有可检测偏好”结果。
- **规格检查器。** 抓出把帧数当秒填、不足一帧的窗口、过长的土狼时间、高频事件震屏、通道过载、缺少无障碍开关等问题。
- **手感报告模板**，附一个用真实工具输出写成的虚构完整示例。
- 技能与 README 均有完整中英文版本。

## 安装

技能就是一个包含 `SKILL.md` 的文件夹，克隆到你的智能体读取技能的位置即可：

```bash
git clone https://github.com/fangdididi/feel-bench.git
```

| 智能体 | 放置位置 |
|---|---|
| **Claude Code** | `~/.claude/skills/feel-bench/`（个人）或 `.claude/skills/feel-bench/`（单个项目） |
| **Codex CLI** | `~/.codex/skills/feel-bench/` 或仓库内 `.agents/skills/feel-bench/`；也可在 `AGENTS.md` 中引用 `SKILL.md` |
| **Cursor** | `.cursor/skills/feel-bench/`，或把 `SKILL.md` 设为项目规则 / 在对话中 `@` 引用 |
| **Gemini CLI、Copilot、Kiro、Windsurf 等** | 把文件夹放进仓库，并在智能体的指令文件（`GEMINI.md`、`.github/copilot-instructions.md` 等）中指向 `feel-bench/SKILL.md` |

示例：

```bash
mkdir -p ~/.claude/skills && git clone https://github.com/fangdididi/feel-bench.git ~/.claude/skills/feel-bench
```

环境要求：辅助工具需要 Python 3.8+（仅标准库）。引擎不限：Godot、Unity、Unreal、Phaser 或自写循环。如需测延迟，准备一部支持慢动作录像的手机。

## 使用

可以这样对智能体说：

- “这个跳跃手感太飘了，帮我用数据调一下，别把关卡弄坏。”
- “给这个角色控制器写一份手感规格，并按 50 Hz 验证。”
- “改完之后这个坑还跳得过去吗？”
- “我们的镜头在笔记本上感觉不一样，查一下原因。”
- “给这两组冲刺参数安排一次盲测。”
- "The jump feels floaty. Fix it without breaking the levels."

辅助命令：

```bash
python3 scripts/feelbench.py lint feel.json
python3 scripts/feelbench.py derive feel.json
python3 scripts/feelbench.py sim feel.json
python3 scripts/feelbench.py windows feel.json
python3 scripts/feelbench.py reach feel.json          # 有坑违背意图时退出码为 1
python3 scripts/feelbench.py smooth 0.15 --ref-fps 60 --fps 30,60,144
python3 scripts/feelbench.py latency --camera-fps 240 --budget-ms 100 22 25 21 27 23 26 22 24 28 23
python3 scripts/feelbench.py abtest 13 3 --ties 2
python3 scripts/feelbench.py --json sim feel.json     # 机器可读输出
python3 -m unittest discover -s tests                 # 32 个测试
```

## 示例

来自 `examples/` 中的虚构平台游戏（数字均为工具真实输出）：

```text
$ python3 scripts/feelbench.py sim examples/feel.json
physics_hz=60.0  full_peak_tiles=3.33  target_peak_tiles=3.5  peak_error_pct=-4.84  apex_ticks=21
target_apex_ticks=20.4  airtime_ticks=36  airtime_s=0.6  min_hop_tiles=0.633  hop_ratio=0.19
formula_jump_velocity=329.412  stepped_jump_velocity=337.55

$ python3 scripts/feelbench.py reach examples/feel.json
name=1-1 first pit  reach_tiles=4.8   spare_tiles=1.8   verdict=CLEAR       intent=CLEAR  matches_intent=True
name=1-3 long pit   reach_tiles=4.8   spare_tiles=-1.2  verdict=IMPOSSIBLE  intent=TIGHT  matches_intent=False
name=1-4 step up    reach_tiles=3.33  spare_tiles=0.33  verdict=TIGHT       intent=TIGHT  matches_intent=True
name=1-5 wall       reach_tiles=None  spare_tiles=None  verdict=TOO HIGH    intent=TOO HIGH  matches_intent=True

$ python3 scripts/feelbench.py abtest 3 13 --ties 2
prefer_a=3  prefer_b=13  no_preference=2  decisive=16  p_value=0.0213  alpha=0.05  verdict=B PREFERRED
```

更干脆的跳跃在盲测中胜出；试验台同时发现它会让 1-3 号坑跳不过去，于是发版前先把坑缩窄。完整过程见 [`examples/report.md`](examples/report.md)。

## 工作流程

1. **简报**：动作、三个词、禁用词、抱怨、平台与物理帧率。
2. **规格**：写 `feel.json` 并 `lint`。
3. **推导与逐帧验证**：`derive`、`sim`、`windows`。
4. **关卡检查**：每次改跳跃或跑动前后都跑 `reach`。
5. **接入引擎**：固定步长、窗口按帧计、指数平滑、调试面板。
6. **测量**：轨迹与 `sim` 核对，慢动作视频测延迟。
7. **反馈清单**：分级、通道、无障碍开关。
8. **盲测 A/B**：只差一处、中性标签、顺序平衡、事先定规则、`abtest`。
9. **报告**：规格差异、前后试验台结果、测量、投票、尚未测试的部分。

## 文件结构

```text
feel-bench/
├── SKILL.md                    # 技能说明（英文）
├── SKILL.zh-CN.md              # 技能说明（中文）
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/
│   └── feelbench.py            # 标准库工具：derive、sim、reach、windows、smooth、latency、abtest、lint
├── tests/
│   └── test_feelbench.py       # 32 个单元测试
├── examples/
│   ├── feel.json               # 改动后的规格（虚构平台游戏）
│   ├── feel.before.json        # 改动前的规格
│   └── report.md               # 完整手感报告示例
└── references/
    ├── word-to-lever.md        # 手感词 -> 杠杆与起始范围
    ├── measuring.md            # 调试面板、轨迹核对、延迟拍摄、预算、盲测脚本
    └── engine-notes.md         # 各引擎物理帧率、固定步长、时间缩放、平滑
```

## 局限

- 模拟只覆盖角色控制器在恒定跑速下的单次跳跃，不模拟斜坡、移动平台、蹬墙跳或刚体物理，这些要在实际版本里检查。
- 距离计算假设以最高速从边缘起跳，土狼时间会再多给一点。
- 延迟数据取决于视频质量：至少按 10 次，并使用玩家的显示设置。
- 符号检验回答的是“玩家是否偏好其中一个”，而不是“好多少”。

## 许可证

MIT © 2026 fangdididi
