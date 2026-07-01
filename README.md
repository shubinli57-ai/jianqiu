# 环形弹簧圈 CadQuery 建模脚本

本仓库提供 `spring_ring_model.py`，用于生成过钻头测井仪器电源模块外侧的 **3 个环形弹簧圈导热结构**，并导出 STEP 文件，便于后续导入 COMSOL 建立接触导热仿真模型。

## 几何背景

- 灌封体外径：36.5 mm
- 灌封体半径：18.25 mm
- 仪器外壳内径：39.38 mm
- 外壳内半径：19.69 mm
- 灌封体与外壳之间的径向间隙：1.44 mm
- 弹簧环数量：3 个
- 默认弹簧环中心半径：18.97 mm，即灌封体半径与外壳内半径之间的中线半径

脚本生成的是带开口角度的空间环形螺旋弹簧圈。每个弹簧环沿周向布置，中心线具有径向和轴向起伏，用圆形弹簧丝截面扫掠生成三维实体。

## 文件说明

- `spring_ring_model.py`：CadQuery 参数化建模脚本。
- `outputs/spring_ring_model.step`：默认 STEP 输出路径，运行脚本后生成。

## 参数说明

脚本中的 `SpringRingParameters` 集中管理所有关键参数：

| 参数 | 含义 | 默认值 |
| --- | --- | --- |
| `potting_radius` | 灌封体半径，单位 mm | `18.25` |
| `shell_inner_radius` | 外壳内半径，单位 mm | `19.69` |
| `spring_center_radius` | 弹簧环中心半径，单位 mm | `(18.25 + 19.69) / 2` |
| `wire_diameter` | 弹簧丝直径，单位 mm | `0.35` |
| `coil_turns` | 单个环形弹簧的螺旋起伏圈数 | `36` |
| `axial_positions` | 3 个弹簧环的轴向 Z 位置，单位 mm | `(-12.0, 0.0, 12.0)` |
| `opening_angle` | 弹簧环开口角度，单位 degree | `25.0` |
| `step_output_path` | STEP 文件输出路径 | `outputs/spring_ring_model.step` |
| `helix_amplitude` | 螺旋中心线起伏幅值，单位 mm；为 `None` 时自动按径向间隙估算 | `None` |
| `points_per_turn` | 每圈离散点数，值越大曲线越平滑 | `18` |

## 安装依赖

建议在本地 Python 虚拟环境中通过 `requirements.txt` 安装 CadQuery：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 可使用 .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` 当前固定为 CadQuery 2.x 主版本范围：

```text
cadquery>=2.4,<3
```

如果当前云端环境没有 CadQuery，或安装 CadQuery 需要较长时间/系统图形依赖，请不要在云端强行安装。直接将本仓库同步到本地，在本地 Python 环境运行即可。

## 运行脚本

```bash
python spring_ring_model.py
```

运行成功后，终端会输出 STEP 文件的绝对路径。最终应生成的 STEP 文件名和路径为：

```text
outputs/spring_ring_model.step
```

如需调整尺寸，直接修改 `spring_ring_model.py` 中 `main()` 函数里的 `SpringRingParameters(...)` 参数即可。例如可调整弹簧丝直径、弹簧圈数、3 个环的轴向位置或开口角度。脚本会自动创建 `outputs/` 目录并导出 `spring_ring_model.step`。

## 当前云端环境检查说明

本仓库脚本已做 Python 语法检查；但当前云端环境未安装 CadQuery，直接运行 `python spring_ring_model.py` 会在 `import cadquery` 处失败并提示 `ModuleNotFoundError: No module named 'cadquery'`。因此，本次未在云端强行安装依赖或导出 STEP 文件。请按上文依赖安装步骤在本地运行脚本生成 `outputs/spring_ring_model.step`。

## 导入 COMSOL

1. 先在本地运行脚本，生成 `outputs/spring_ring_model.step`。
2. 打开 COMSOL Multiphysics。
3. 在模型树中进入 **Geometry**。
4. 选择 **Import**。
5. 文件类型选择 STEP，导入 `outputs/spring_ring_model.step`。
6. 点击 **Import** 或 **Build Selected** 生成几何。
7. 根据仿真需要，可继续创建或导入灌封体圆柱、外壳内壁圆柱，并设置弹簧环与外壳/灌封体之间的接触对或热接触边界。
8. 如果导入后几何过于复杂，可在脚本中降低 `coil_turns` 或 `points_per_turn`，先用于网格和接触设置调试；最终仿真再提高曲线精度。

## 建模注意事项

- 本脚本默认单位为 mm。导入 COMSOL 后请确认几何单位设置为 mm，或在导入设置中进行正确缩放。
- 默认 `wire_diameter=0.35` mm 是用于示例的保守值，实际仿真应根据真实弹簧丝规格修改。
- `helix_amplitude=None` 时，脚本会根据 1.44 mm 径向间隙和弹簧丝半径自动估算螺旋起伏幅值，避免弹簧丝实体明显穿入灌封体或外壳。
- `opening_angle` 用于形成装配开口；如果希望闭合环，可将开口角度设为 `0`，但实际弹性装配通常建议保留开口。
