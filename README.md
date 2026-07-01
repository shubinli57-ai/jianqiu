# 微开口 Clean 版单个环形螺旋弹簧本体 CadQuery 模型

本仓库提供 `spring_ring_model.py`，用于生成 **一个单独的环形螺旋弹簧本体** 并导出 STEP 文件。该版本在弹簧首尾位置保留极小开口，用于避免完全闭合扫掠在接缝处产生无效几何，从而提高导入 COMSOL 时的 STEP 几何稳定性。

## 模型范围

本脚本只生成弹簧本体：

- 不生成平台；
- 不生成外壳；
- 不生成环形槽；
- 不生成任何辅助实体、参考圆柱或定位几何；
- STEP 文件中只应包含 1 个弹簧 solid 实体。

坐标约定：

- Z 轴为弹簧环中心轴线；
- 弹簧环位于 XY 平面内；
- 弹簧中心线围绕 Z 轴形成接近闭合的紧凑圆环；
- 导入 COMSOL 后，可复制该弹簧本体并沿 Z 轴移动到不同轴向位置。

## 微开口设计

完全闭合的环形螺旋弹簧在 sweep 闭合位置可能产生无效面片、缝合失败或局部面不一致。为避免该问题，本版本不再强制中心线首尾闭合，而是在首尾位置保留非常小的开口：

- 默认 `open_angle = 1°`；
- 如果 1° 仍导致实体无效，程序会自动尝试 `2°`、`3°`；
- 如果仍无效，程序会在 `3°` 开口下自动尝试 `coil_count = 50` 和 `coil_count = 40`；
- 开口最大不超过 `3°`，肉眼基本不明显，不改变整体弹簧结构效果；
- 该小开口只用于提高 STEP 几何稳定性，最终 STEP 仍只包含弹簧本体。

自动尝试顺序为：

1. `open_angle = 1°`，`coil_count = 60`；
2. `open_angle = 2°`，`coil_count = 60`；
3. `open_angle = 3°`，`coil_count = 60`；
4. `open_angle = 3°`，`coil_count = 50`；
5. `open_angle = 3°`，`coil_count = 40`。

## 默认尺寸

当前版本保持上一版的大致外形尺寸和紧凑视觉效果：

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `envelope_center_radius` | 弹簧整体包络中心半径 | `18.82` mm |
| `envelope_radius` | 弹簧整体截面包络半径 | `0.87` mm |
| `wire_diameter` | 弹簧丝直径 | `0.15` mm |
| `coil_count` | 环向弹簧圈数 | `60` |
| `open_angle` | 弹簧首尾微开口角度 | `1.0°` |
| `points_per_coil` | 每圈中心线离散点数 | `64` |
| `step_output_path` | STEP 输出路径 | `outputs/spring_ring_single_open_clean.step` |

由默认参数得到：

- 弹簧外侧最大半径约为 `18.82 + 0.87 = 19.69 mm`；
- 弹簧内侧最小半径约为 `18.82 - 0.87 = 17.95 mm`；
- 弹簧丝半径 `wire_radius = wire_diameter / 2 = 0.075 mm`；
- 螺旋中心线小半径 `helix_minor_radius = envelope_radius - wire_radius = 0.795 mm`；
- 默认中心线采样点数为 `60 * 64 + 1 = 3841`，满足不少于 2500 点的要求。

注意：`envelope_radius` 是弹簧整体截面包络半径，不是弹簧丝半径；`wire_radius` 才是弹簧丝半径。

## 几何稳定性处理

脚本做了以下处理以提高 STEP 导入稳定性：

1. 使用开口的环形螺旋中心线，`theta` 范围为 `0` 到 `2π - open_angle`；
2. 不再使用 `periodic=True`，也不再强制中心线首尾闭合；
3. 中心线采样点数不少于 2500；
4. 使用圆截面沿开口样条路径扫掠生成 solid 实体；
5. 扫掠后执行 `.clean()`；
6. 导出前检查 solid 数量和 CadQuery `isValid()` 结果；
7. 如果当前参数生成无效实体，会自动尝试下一组 `open_angle` 和 `coil_count`；
8. 只有生成单个有效 solid 时才导出 STEP。

## 安装依赖

建议在本地 Python 虚拟环境中安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 可使用 .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` 当前保留 CadQuery 2.x 版本范围：

```text
cadquery>=2.4,<3
```

如果当前云端环境没有 CadQuery，或安装 CadQuery 需要较长时间/系统图形依赖，请不要在云端强行安装。直接将本仓库同步到本地，在本地 Python 环境运行即可。

## 运行脚本并生成 STEP

```bash
python spring_ring_model.py
```

运行时终端会打印每次尝试采用的 `open_angle`、`coil_count`、`wire_diameter`、中心线采样点数、solid 数量和 `isValid()` 结果。成功后会打印最终采用的参数和 STEP 文件路径。

最终输出文件为：

```text
outputs/spring_ring_single_open_clean.step
```

## 修改弹簧尺寸和密度

打开 `spring_ring_model.py`，修改 `main()` 函数中的 `SpringRingParameters(...)`：

```python
base_params = SpringRingParameters(
    envelope_center_radius=18.82,
    envelope_radius=0.87,
    wire_diameter=0.15,
    coil_count=60,
    open_angle=1.0,
    points_per_coil=64,
    step_output_path="outputs/spring_ring_single_open_clean.step",
)
```

常见修改方式：

- 修改弹簧丝径：调整 `wire_diameter`。
- 修改弹簧圈密度：调整 `coil_count`；如果几何仍无效，可尝试 `50` 或 `40`。
- 修改微开口：调整 `open_angle`，建议保持在 `1°` 到 `3°` 之间。
- 修改整体外形尺寸：调整 `envelope_radius` 和 `envelope_center_radius`。
- 修改输出文件名：调整 `step_output_path`。

## 在 COMSOL 中使用

1. 本地运行脚本，生成 `outputs/spring_ring_single_open_clean.step`。
2. 打开 COMSOL Multiphysics。
3. 在模型树中进入 **Geometry**。
4. 选择 **Import**，文件类型选择 STEP。
5. 导入 `outputs/spring_ring_single_open_clean.step`。
6. 点击 **Import** 或 **Build Selected** 生成几何。
7. 如需多个弹簧环，可在 COMSOL 中复制该单个弹簧本体，并沿 Z 轴移动到不同轴向位置。

## 当前云端环境说明

本仓库脚本已通过 Python 语法检查。当前云端环境未安装 CadQuery，直接运行 `python spring_ring_model.py` 会在 `import cadquery` 处提示 `ModuleNotFoundError: No module named 'cadquery'`，因此未在云端强行安装依赖或导出 STEP 文件。请按上文步骤在本地安装依赖并生成 STEP。
