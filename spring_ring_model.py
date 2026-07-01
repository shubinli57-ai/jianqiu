"""
生成单个嵌入式环形螺旋弹簧圈的 CadQuery 参数化模型。

坐标约定：
- 仪器轴线沿 Z 轴；
- 弹簧环位于 XY 平面内，并围绕 Z 轴闭合成圆环；
- 导入 COMSOL 后，可沿 Z 轴复制/移动该单个弹簧环到不同轴向位置。

默认结构尺寸：
- 平台/导热套外半径 platform_radius = 18.25 mm；
- 外壳内半径 shell_inner_radius = 19.69 mm；
- 环形槽深度 groove_depth = 0.30 mm；
- 弹簧整体包络半径 envelope_radius = (gap + groove_depth) / 2 = 0.87 mm；
- 弹簧包络中心半径 envelope_center_radius = shell_inner_radius - envelope_radius = 18.82 mm；
- 弹簧实体外侧最大半径等于 shell_inner_radius，表示装配后等效接触外壳内壁；
- 弹簧实体内侧最小半径接近 groove_bottom_radius，表示嵌入槽底附近。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin, sqrt
from pathlib import Path

import cadquery as cq
from cadquery import Plane


@dataclass(frozen=True)
class SpringRingParameters:
    """单个嵌入式环形弹簧圈参数，长度单位均为 mm。"""

    # 平台/导热套外半径：弹簧环安装槽开在该外圆附近。
    platform_radius: float = 18.25

    # 外壳内半径：装配后弹簧外侧等效接触的圆柱内壁半径。
    shell_inner_radius: float = 19.69

    # 环形槽深度：槽底相对平台/导热套外圆向内的径向深度。
    groove_depth: float = 0.30

    # 弹簧丝直径：真实金属丝圆截面直径；不是弹簧整体包络直径。
    wire_diameter: float = 0.20

    # 环向弹簧圈数：小螺旋沿完整圆环绕行的圈数，建议取 80 或 90 以获得紧凑效果。
    coil_count: int = 90

    # 每圈离散点数：值越大，中心线越圆滑，STEP 文件也越大。
    points_per_coil: int = 12

    # STEP 文件输出路径：默认输出单个 0.30 mm 槽深的嵌入式弹簧环模型。
    step_output_path: str = "outputs/spring_ring_single_groove0p3.step"

    @property
    def gap(self) -> float:
        """径向间隙：外壳内半径与平台/导热套外半径之差。"""
        return self.shell_inner_radius - self.platform_radius

    @property
    def groove_bottom_radius(self) -> float:
        """槽底半径：平台/导热套外半径减去槽深。"""
        return self.platform_radius - self.groove_depth

    @property
    def envelope_radius(self) -> float:
        """弹簧整体截面包络半径：由径向间隙和槽深共同决定。"""
        return (self.gap + self.groove_depth) / 2

    @property
    def envelope_center_radius(self) -> float:
        """弹簧包络中心半径：保证外侧包络刚好接触外壳内壁。"""
        return self.shell_inner_radius - self.envelope_radius

    @property
    def wire_radius(self) -> float:
        """弹簧丝半径：弹簧丝直径的一半。"""
        return self.wire_diameter / 2

    @property
    def helix_minor_radius(self) -> float:
        """螺旋中心线小半径：等于包络半径减去弹簧丝半径。"""
        return self.envelope_radius - self.wire_radius


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


def validate_parameters(params: SpringRingParameters) -> SpringRingParameters:
    """检查关键几何参数，避免生成不合理或不可扫掠的模型。"""
    if params.platform_radius <= 0 or params.shell_inner_radius <= 0:
        raise ValueError("平台/导热套外半径和外壳内半径必须为正数。")
    if params.shell_inner_radius <= params.platform_radius:
        raise ValueError("外壳内半径必须大于平台/导热套外半径。")
    if params.groove_depth <= 0:
        raise ValueError("环形槽深度必须为正数。")
    if params.wire_diameter <= 0:
        raise ValueError("弹簧丝直径必须为正数。")
    if params.helix_minor_radius <= 0:
        raise ValueError("弹簧丝半径不能大于或等于弹簧整体包络半径。")
    if params.coil_count < 3:
        raise ValueError("环向弹簧圈数过少，无法形成紧凑环形螺旋弹簧。")
    if params.points_per_coil < 8:
        raise ValueError("每圈离散点数建议不小于 8。")
    return params


def spring_centerline_points(params: SpringRingParameters) -> list[tuple[float, float, float]]:
    """用参数方程生成围绕 Z 轴闭合的环形螺旋弹簧中心线。"""
    params = validate_parameters(params)
    total_points = params.coil_count * params.points_per_coil
    points: list[tuple[float, float, float]] = []

    for index in range(total_points + 1):
        theta = 2 * pi * index / total_points
        phase = params.coil_count * theta

        # radial_radius 是中心线到 Z 轴的瞬时半径。
        # 其最大/最小值再加/减 wire_radius 后，对应弹簧实体外/内包络。
        radial_radius = params.envelope_center_radius + params.helix_minor_radius * cos(phase)

        # z 方向起伏与径向起伏相差 90°，形成紧凑的环形螺旋中心线。
        z = params.helix_minor_radius * sin(phase)

        points.append((radial_radius * cos(theta), radial_radius * sin(theta), z))

    return points


def _profile_plane_at_path_start(points: list[tuple[float, float, float]]) -> Plane:
    """创建经过中心线起点且近似垂直于起点切向的扫掠截面平面。"""
    start = points[0]
    next_point = points[1]
    tangent = _unit_vector(
        (next_point[0] - start[0], next_point[1] - start[1], next_point[2] - start[2])
    )
    reference = (0.0, 0.0, 1.0)
    x_direction = _cross(reference, tangent)
    if sqrt(x_direction[0] ** 2 + x_direction[1] ** 2 + x_direction[2] ** 2) < 1e-9:
        reference = (1.0, 0.0, 0.0)
        x_direction = _cross(reference, tangent)
    return Plane(origin=start, xDir=_unit_vector(x_direction), normal=tangent)


def make_single_spring_ring(params: SpringRingParameters) -> cq.Workplane:
    """创建单个完整闭合的嵌入式环形螺旋弹簧实体。"""
    params = validate_parameters(params)
    points = spring_centerline_points(params)

    # 使用 periodic=True 创建闭合周期样条，避免用直线段闭合造成局部折角。
    # 最后一个点与第一个点重合，仅用于几何尺寸校核；建样条时去掉重复末点。
    path = cq.Workplane("XY").spline(points[:-1], periodic=True)
    profile_plane = _profile_plane_at_path_start(points)

    return (
        cq.Workplane(profile_plane)
        .circle(params.wire_radius)
        .sweep(path, isFrenet=True)
    )


def export_step(model: cq.Workplane, output_path: str | Path) -> Path:
    """导出 STEP 文件，供 COMSOL 或其他 CAE/CAD 软件导入。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(path))
    return path


def main() -> None:
    """脚本入口：生成 1 个标准嵌入式弹簧环并导出 STEP 文件。"""
    params = SpringRingParameters(
        # 可在此处按实际结构尺寸修改参数。
        platform_radius=18.25,
        shell_inner_radius=19.69,
        groove_depth=0.30,
        wire_diameter=0.20,
        coil_count=90,
        points_per_coil=12,
        step_output_path="outputs/spring_ring_single_groove0p3.step",
    )
    model = make_single_spring_ring(params)
    output = export_step(model, params.step_output_path)
    print(f"STEP 文件已导出：{output.resolve()}")
    print(f"外侧最大半径 = {params.envelope_center_radius + params.envelope_radius:.3f} mm")
    print(f"内侧最小半径 = {params.envelope_center_radius - params.envelope_radius:.3f} mm")


if __name__ == "__main__":
    main()
