# Clean 版单个环形螺旋弹簧本体 CadQuery 模型

本仓库提供 `spring_ring_model.py`，用于生成 **一个单独的环形螺旋弹簧本体** 并导出 STEP 文件。该 clean 版本的目标是保持弹簧外观紧凑、闭合和尺寸基本不变，同时改善 STEP 几何质量，尽量降低导入 COMSOL 时出现“面与面不一致”等几何警告的概率。

## 模型范围

本脚本只生成弹簧本体：

- 不生成平台；
- 不生成外壳；
- 不生成环形槽；
- 不生成辅助实体、参考圆柱或定位几何；
- STEP 文件中只应包含 1 个弹簧 solid 实体。

坐标约定：

- Z 轴为弹簧环中心轴线；
- 弹簧环位于 XY 平面内；
- 弹簧中心线围绕 Z 轴形成完整闭合圆环；
- 导入 COMSOL 后，可复制该弹簧本体并沿 Z 轴移动到不同轴向位置。

## 默认尺寸

当前 clean 版本保留上一版的大致外形尺寸：

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `envelope_center_radius` | 弹簧整体包络中心半径 | `18.82` mm |
| `envelope_radius` | 弹簧整体截面包络半径 | `0.87` mm |
| `wire_diameter` | 弹簧丝直径 | `0.15` mm |
| `coil_count` | 环向弹簧圈数 | `70` |
| `points_per_coil` | 每圈中心线离散点数 | `46` |
| `step_output_path` | STEP 输出路径 | `outputs/spring_ring_single_clean.step` |

由默认参数得到：

- 弹簧外侧最大半径约为 `18.82 + 0.87 = 19.69 mm`；
- 弹簧内侧最小半径约为 `18.82 - 0.87 = 17.95 mm`；
- 弹簧丝半径 `wire_radius = wire_diameter / 2 = 0.075 mm`；
- 螺旋中心线小半径 `helix_minor_radius = envelope_radius - wire_radius = 0.795 mm`；
- 默认中心线采样点数为 `70 * 46 + 1 = 3221`，用于提高闭合和扫掠稳定性。

注意：`envelope_radius` 是弹簧整体截面包络半径，不是弹簧丝半径；`wire_radius` 才是弹簧丝半径。

## 几何质量优化

为改善 COMSOL 导入稳定性，脚本做了以下处理：

1. 使用首尾位置连续、切向连续的周期参数方程生成闭合中心线；
2. 使用 `periodic=True` 创建闭合周期样条，避免用直线段闭合产生折角；
3. 默认中心线采样点数超过 3000；
4. 使用较细弹簧丝直径 `0.15 mm` 和较低但仍紧凑的 `70` 圈，降低局部自相交风险；
5. 使用圆截面沿闭合路径扫掠生成 solid 实体，而不是 wire、shell 或 surface；
6. 扫掠后执行 `.clean()`；
7. 导出 STEP 前检查 solid 数量和 CadQuery `isValid()` 结果；
8. 如果实体无效，脚本会打印提示并停止导出，避免静默输出错误 STEP。

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

运行成功后，终端会打印：

- CadQuery 形状类型；
- solid 数量；
- `isValid()` 几何有效性检查结果；
- STEP 文件绝对路径；
- 中心线采样点数；
- 弹簧外侧最大半径和内侧最小半径。

最终输出文件为：

```text
outputs/spring_ring_single_clean.step
```

## 修改弹簧尺寸和密度

打开 `spring_ring_model.py`，修改 `main()` 函数中的 `SpringRingParameters(...)`：

```python
params = SpringRingParameters(
    envelope_center_radius=18.82,
    envelope_radius=0.87,
    wire_diameter=0.15,
    coil_count=70,
    points_per_coil=46,
    step_output_path="outputs/spring_ring_single_clean.step",
)
```

常见修改方式：

- 修改弹簧丝径：调整 `wire_diameter`，建议先尝试 `0.15` 或 `0.18`。
- 修改弹簧圈密度：调整 `coil_count`，建议在 `60` 到 `80` 之间；如果 COMSOL 导入仍有几何警告，可先降低到 `60` 或 `65`。
- 修改整体外形尺寸：调整 `envelope_radius` 和 `envelope_center_radius`。
- 修改输出文件名：调整 `step_output_path`，例如 `outputs/spring_ring_single_clean_coil60.step`。

## 在 COMSOL 中使用

1. 本地运行脚本，生成 `outputs/spring_ring_single_clean.step`。
2. 打开 COMSOL Multiphysics。
3. 在模型树中进入 **Geometry**。
4. 选择 **Import**，文件类型选择 STEP。
5. 导入 `outputs/spring_ring_single_clean.step`。
6. 点击 **Import** 或 **Build Selected** 生成几何。
7. 如需多个弹簧环，可在 COMSOL 中复制该单个弹簧本体，并沿 Z 轴移动到不同轴向位置。

## 当前云端环境说明

本仓库脚本已通过 Python 语法检查。当前云端环境未安装 CadQuery，直接运行 `python spring_ring_model.py` 会在 `import cadquery` 处提示 `ModuleNotFoundError: No module named 'cadquery'`，因此未在云端强行安装依赖或导出 STEP 文件。请按上文步骤在本地安装依赖并生成 STEP。
