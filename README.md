# 单个嵌入式环形弹簧圈 CadQuery 建模脚本

本仓库提供 `spring_ring_model.py`，用于生成过钻头测井仪器电源模块导热结构中的 **单个嵌入式环形螺旋弹簧圈**，并导出 STEP 文件，便于后续导入 COMSOL 做局部接触/导热验证。

## 模型定位

本版本只生成 **1 个标准弹簧环**，不再一次生成 3 个弹簧环。这样导入 COMSOL 后，可以根据实际装配方案自行复制 3 个弹簧环，并沿仪器轴向移动到不同位置。

坐标约定如下：

- 仪器轴线沿 **Z 轴**；
- 弹簧环位于 **XY 平面**内；
- 弹簧中心线围绕 **Z 轴**形成完整闭合圆环；
- 在 COMSOL 中复制后，可主要沿 Z 轴移动，也可按需要旋转或阵列。

## 几何背景

- 平台/导热套外半径 `platform_radius`：18.25 mm
- 外壳内半径 `shell_inner_radius`：19.69 mm
- 径向间隙 `gap`：1.44 mm
- 环形槽深度 `groove_depth`：0.30 mm
- 槽底半径 `groove_bottom_radius = platform_radius - groove_depth`：17.95 mm
- 弹簧整体包络半径 `envelope_radius = (gap + groove_depth) / 2`：0.87 mm
- 弹簧包络中心半径 `envelope_center_radius = shell_inner_radius - envelope_radius`：18.82 mm

该模型表示装配后的等效接触状态：弹簧实体外侧最大半径等于外壳内半径 19.69 mm，即弹簧外侧刚好与外壳内壁接触；弹簧实体内侧最小半径接近槽底半径 17.95 mm，即弹簧嵌入环形槽底附近。

## 建模方法

脚本使用环形螺旋弹簧中心线的参数方程：

- `theta` 从 0 到 `2π`，控制弹簧绕 Z 轴闭合成环；
- `coil_count` 控制小螺旋沿环向绕行的圈数，默认 90，模型更紧凑；
- `envelope_center_radius` 控制弹簧整体包络中心半径；
- `helix_minor_radius = envelope_radius - wire_radius`，其中 `wire_radius = wire_diameter / 2`；
- 用圆形截面沿闭合周期样条中心线扫掠，生成真实感更强的紧凑弹簧丝实体。

注意：`envelope_radius` 是弹簧整体截面包络半径，不是弹簧丝半径；`wire_radius` 才是弹簧丝半径。

## 文件说明

- `spring_ring_model.py`：CadQuery 参数化建模脚本。
- `requirements.txt`：本地运行所需 Python 依赖。
- `outputs/spring_ring_single_groove0p3.step`：默认 STEP 输出路径，运行脚本后生成。

## 参数说明

脚本中的 `SpringRingParameters` 集中管理关键参数：

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `platform_radius` | 平台/导热套外半径，单位 mm | `18.25` |
| `shell_inner_radius` | 外壳内半径，单位 mm | `19.69` |
| `groove_depth` | 环形槽深度，单位 mm | `0.30` |
| `wire_diameter` | 弹簧丝直径，单位 mm | `0.20` |
| `coil_count` | 环向弹簧圈数，建议 80 或 90 | `90` |
| `points_per_coil` | 每圈离散点数，值越大曲线越平滑 | `12` |
| `step_output_path` | STEP 文件输出路径 | `outputs/spring_ring_single_groove0p3.step` |

`gap`、`groove_bottom_radius`、`envelope_radius`、`envelope_center_radius`、`wire_radius` 和 `helix_minor_radius` 会由上述参数自动计算。

## 安装依赖

建议在本地 Python 虚拟环境中安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 可使用 .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` 当前内容为：

```text
cadquery>=2.4,<3
```

如果当前云端环境没有 CadQuery，或安装 CadQuery 需要较长时间/系统图形依赖，请不要在云端强行安装。直接将本仓库同步到本地，在本地 Python 环境运行即可。

## 运行脚本并生成 STEP

```bash
python spring_ring_model.py
```

运行成功后，终端会输出 STEP 文件的绝对路径。最终应生成的 STEP 文件名和路径为：

```text
outputs/spring_ring_single_groove0p3.step
```

## 如何修改关键参数

打开 `spring_ring_model.py`，修改 `main()` 函数中的 `SpringRingParameters(...)`：

```python
params = SpringRingParameters(
    platform_radius=18.25,
    shell_inner_radius=19.69,
    groove_depth=0.30,
    wire_diameter=0.20,
    coil_count=90,
    points_per_coil=12,
    step_output_path="outputs/spring_ring_single_groove0p3.step",
)
```

常见修改方式：

- 修改槽深：调整 `groove_depth`。例如 0.40 mm 槽深可设为 `groove_depth=0.40`。
- 修改弹簧丝径：调整 `wire_diameter`。例如更细弹簧丝可设为 `wire_diameter=0.18`。
- 修改环向圈数：调整 `coil_count`。建议优先使用 80 或 90；数值越大，弹簧越紧凑，几何和网格也越复杂。
- 修改输出文件名：调整 `step_output_path`。例如 `outputs/spring_ring_single_groove0p4.step`。

## 在 COMSOL 中使用

1. 本地运行脚本，生成 `outputs/spring_ring_single_groove0p3.step`。
2. 打开 COMSOL Multiphysics。
3. 在模型树中进入 **Geometry**。
4. 选择 **Import**，文件类型选择 STEP。
5. 导入 `outputs/spring_ring_single_groove0p3.step`。
6. 点击 **Import** 或 **Build Selected** 生成几何。
7. 如需 3 个弹簧环，可在 COMSOL 中复制该单个弹簧环，并沿 Z 轴移动到不同轴向位置。
8. 与外壳内壁设置热接触或等效接触导热边界时，可将弹簧外侧视为装配后刚好接触外壳内壁的状态。

## 当前云端环境说明

本仓库脚本已通过 Python 语法检查。当前云端环境未安装 CadQuery，直接运行 `python spring_ring_model.py` 会在 `import cadquery` 处提示 `ModuleNotFoundError: No module named 'cadquery'`，因此未在云端强行安装依赖或导出 STEP 文件。请按上文步骤在本地安装依赖并生成 STEP。
