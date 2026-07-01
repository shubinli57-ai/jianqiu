"""
用于生成过钻头测井仪器电源模块环形弹簧圈导热结构的 CadQuery 参数化模型。

模型说明：
- 灌封体外径 36.5 mm（半径 18.25 mm）；
- 仪器外壳内径 39.38 mm（半径 19.69 mm）；
- 径向间隙 1.44 mm；
- 默认生成 3 个沿轴向分布的开口环形弹簧圈，并导出为 STEP，便于导入 COMSOL。

运行前请先安装 CadQuery：
    pip install cadquery

运行：
    python spring_ring_model.py
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, radians, sin, sqrt
from pathlib import Path
from typing import Iterable

import cadquery as cq
from cadquery import Plane


def _unit_vector(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    """返回单位向量，用于定义扫掠截面的工作平面。"""
    length = sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    if length == 0:
        raise ValueError("无法根据零长度向量创建工作平面。")
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _cross(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> tuple[float, float, float]:
    """计算三维向量叉乘。"""
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


@dataclass(frozen=True)
class SpringRingParameters:
    """环形弹簧圈参数，长度单位均为 mm，角度单位为 degree。"""

    # 灌封体半径：电源模块灌封体外圆半径，默认 36.5 mm / 2 = 18.25 mm。
    potting_radius: float = 18.25

    # 外壳内半径：仪器外壳内壁半径，默认 39.38 mm / 2 = 19.69 mm。
    shell_inner_radius: float = 19.69

    # 弹簧环中心半径：弹簧圈整体环形中心线的基准半径，默认取径向间隙中线。
    spring_center_radius: float = (18.25 + 19.69) / 2

    # 弹簧丝直径：实际金属丝截面直径；用于扫掠生成圆形截面实体。
    wire_diameter: float = 0.35

    # 环形弹簧圈数：单个弹簧环沿周向绕行时的螺旋起伏圈数。
    coil_turns: int = 36

    # 弹簧环轴向位置：3 个弹簧环在仪器轴向 Z 方向的位置列表。
    axial_positions: tuple[float, ...] = (-12.0, 0.0, 12.0)

    # 开口角度：每个弹簧环预留的周向缺口角度，便于装配和形成弹性开口。
    opening_angle: float = 25.0

    # STEP 文件输出路径：可为 .step/.stp 文件；父目录不存在时会自动创建。
    step_output_path: str = "outputs/spring_ring_model.step"

    # 螺旋摆幅半径：弹簧圈中心线相对环形中心半径的径向/轴向起伏幅值。
    # 默认根据径向间隙和弹簧丝半径自动计算，以避免穿入灌封体或外壳。
    helix_amplitude: float | None = None

    # 每一圈离散点数：数值越大，导出的 STEP 曲线越平滑，文件也会更大。
    points_per_turn: int = 18


def _validated_parameters(params: SpringRingParameters) -> SpringRingParameters:
    """检查关键几何参数，避免生成明显不合理的模型。"""
    if params.potting_radius <= 0 or params.shell_inner_radius <= 0:
        raise ValueError("灌封体半径和外壳内半径必须为正数。")
    if params.shell_inner_radius <= params.potting_radius:
        raise ValueError("外壳内半径必须大于灌封体半径。")
    if not (params.potting_radius < params.spring_center_radius < params.shell_inner_radius):
        raise ValueError("弹簧环中心半径必须位于灌封体半径和外壳内半径之间。")
    if params.wire_diameter <= 0:
        raise ValueError("弹簧丝直径必须为正数。")
    if params.coil_turns < 1:
        raise ValueError("环形弹簧圈数必须至少为 1。")
    if not (0 <= params.opening_angle < 180):
        raise ValueError("开口角度建议设置在 [0, 180) 度范围内。")
    if params.points_per_turn < 8:
        raise ValueError("每一圈离散点数建议不小于 8。")
    return params


def _auto_helix_amplitude(params: SpringRingParameters) -> float:
    """根据径向间隙自动估算螺旋摆幅半径。"""
    radial_clearance = params.shell_inner_radius - params.potting_radius
    wire_radius = params.wire_diameter / 2
    available_radial_amplitude = radial_clearance / 2 - wire_radius
    if available_radial_amplitude <= 0:
        raise ValueError("弹簧丝直径过大，已超过灌封体与外壳之间可用径向间隙。")
    return min(available_radial_amplitude * 0.85, params.wire_diameter * 1.2)


def _ring_centerline_points(
    params: SpringRingParameters, axial_position: float
) -> list[tuple[float, float, float]]:
    """生成单个开口环形弹簧圈的三维中心线点。"""
    amplitude = (
        params.helix_amplitude
        if params.helix_amplitude is not None
        else _auto_helix_amplitude(params)
    )
    start_angle = radians(params.opening_angle / 2)
    end_angle = radians(360 - params.opening_angle / 2)
    sweep_angle = end_angle - start_angle
    point_count = max(int(params.coil_turns * params.points_per_turn), 24)

    points: list[tuple[float, float, float]] = []
    for index in range(point_count + 1):
        fraction = index / point_count
        theta = start_angle + sweep_angle * fraction
        phase = 2 * pi * params.coil_turns * fraction

        # 径向起伏：模拟环形弹簧圈绕圆周方向的螺旋波动。
        radius = params.spring_center_radius + amplitude * cos(phase)

        # 轴向起伏：与径向起伏相差 90° 相位，形成空间螺旋中心线。
        z = axial_position + amplitude * sin(phase)

        points.append((radius * cos(theta), radius * sin(theta), z))
    return points


def make_spring_ring(params: SpringRingParameters, axial_position: float) -> cq.Workplane:
    """创建单个开口环形弹簧圈实体。"""
    params = _validated_parameters(params)
    centerline = _ring_centerline_points(params, axial_position)
    path = cq.Workplane("XY").spline(centerline)
    wire_radius = params.wire_diameter / 2

    # 扫掠截面必须尽量垂直于路径起点切向。
    # 这里用前两个中心线点估算切向，并创建一个经过起点的自定义工作平面，
    # 避免固定使用 XY/YZ 平面时截面与三维样条路径不垂直而导致扫掠失败。
    start = centerline[0]
    next_point = centerline[1]
    tangent = _unit_vector(
        (next_point[0] - start[0], next_point[1] - start[1], next_point[2] - start[2])
    )
    reference = (0.0, 0.0, 1.0)
    x_direction = _cross(reference, tangent)
    if sqrt(x_direction[0] ** 2 + x_direction[1] ** 2 + x_direction[2] ** 2) < 1e-9:
        reference = (1.0, 0.0, 0.0)
        x_direction = _cross(reference, tangent)
    profile_plane = Plane(origin=start, xDir=_unit_vector(x_direction), normal=tangent)

    return cq.Workplane(profile_plane).circle(wire_radius).sweep(path, isFrenet=True)


def make_three_spring_rings(params: SpringRingParameters) -> cq.Workplane:
    """按给定轴向位置生成 3 个弹簧环并合并为一个模型。"""
    params = _validated_parameters(params)
    if len(params.axial_positions) != 3:
        raise ValueError("本脚本默认生成 3 个弹簧环，请提供 3 个轴向位置。")

    rings: Iterable[cq.Workplane] = (
        make_spring_ring(params, z) for z in params.axial_positions
    )
    model: cq.Workplane | None = None
    for ring in rings:
        model = ring if model is None else model.union(ring)
    if model is None:
        raise RuntimeError("未生成任何弹簧环。")
    return model


def export_step(model: cq.Workplane, output_path: str | Path) -> Path:
    """导出 STEP 文件，供 COMSOL 或其他 CAE/CAD 软件导入。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(path))
    return path


def main() -> None:
    """脚本入口：使用默认参数生成 3 个弹簧环并导出 STEP 文件。"""
    params = SpringRingParameters(
        # 可在此处按实际结构尺寸修改参数。
        potting_radius=18.25,
        shell_inner_radius=19.69,
        spring_center_radius=(18.25 + 19.69) / 2,
        wire_diameter=0.35,
        coil_turns=36,
        axial_positions=(-12.0, 0.0, 12.0),
        opening_angle=25.0,
        step_output_path="outputs/spring_ring_model.step",
    )
    model = make_three_spring_rings(params)
    output = export_step(model, params.step_output_path)
    print(f"STEP 文件已导出：{output.resolve()}")


if __name__ == "__main__":
    main()
