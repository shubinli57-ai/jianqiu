"""
生成单个微开口 clean 版环形螺旋弹簧本体的 CadQuery 参数化模型。

模型目标：
- STEP 文件中只包含弹簧本体，不包含平台、外壳、环形槽或任何辅助实体；
- 弹簧环位于 XY 平面内，并围绕 Z 轴形成几乎闭合的紧凑圆环；
- 在首尾位置保留极小开口，避免完全闭合扫掠在接缝位置产生无效几何；
- 导出前检查 solid 数量和 CadQuery isValid()，只导出有效弹簧实体。

坐标约定：
- Z 轴为弹簧环中心轴线；
- XY 平面为弹簧环中面；
- 弹簧外侧最大半径约为 envelope_center_radius + envelope_radius = 19.69 mm；
- 弹簧内侧最小半径约为 envelope_center_radius - envelope_radius = 17.95 mm。
"""

from __future__ import annotations

from dataclasses import replace, dataclass
from math import cos, pi, radians, sin, sqrt
from pathlib import Path
from typing import Iterable

import cadquery as cq
from cadquery import Plane


@dataclass(frozen=True)
class SpringRingParameters:
    """单个微开口环形螺旋弹簧本体参数，长度单位为 mm，角度单位为 degree。"""

    # 弹簧整体包络中心半径：决定弹簧本体环形中心位置。
    envelope_center_radius: float = 18.82

    # 弹簧整体截面包络半径：不是弹簧丝半径；决定整体外/内包络尺寸。
    envelope_radius: float = 0.87

    # 弹簧丝直径：真实金属丝圆截面直径。
    wire_diameter: float = 0.15

    # 环向弹簧圈数：小螺旋沿圆环绕行的圈数；默认 60，兼顾紧凑外观和几何稳定性。
    coil_count: int = 60

    # 开口角度：首尾保留的极小周向开口，默认 1°，肉眼基本不明显。
    open_angle: float = 1.0

    # 每圈离散点数：默认 64，40 圈时中心线采样点数仍不少于 2500。
    points_per_coil: int = 64

    # STEP 文件输出路径：微开口 clean 版单个弹簧本体模型。
    step_output_path: str = "outputs/spring_ring_single_open_clean.step"

    @property
    def wire_radius(self) -> float:
        """弹簧丝半径：弹簧丝直径的一半。"""
        return self.wire_diameter / 2

    @property
    def helix_minor_radius(self) -> float:
        """螺旋中心线小半径：等于整体包络半径减去弹簧丝半径。"""
        return self.envelope_radius - self.wire_radius

    @property
    def outer_radius(self) -> float:
        """弹簧实体外侧最大半径。"""
        return self.envelope_center_radius + self.envelope_radius

    @property
    def inner_radius(self) -> float:
        """弹簧实体内侧最小半径。"""
        return self.envelope_center_radius - self.envelope_radius

    @property
    def sample_count(self) -> int:
        """开口中心线离散段数。"""
        return self.coil_count * self.points_per_coil


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
    """检查关键几何参数，避免生成不合理或不可扫掠的弹簧实体。"""
    if params.envelope_center_radius <= 0:
        raise ValueError("弹簧整体包络中心半径必须为正数。")
    if params.envelope_radius <= 0:
        raise ValueError("弹簧整体包络半径必须为正数。")
    if params.wire_diameter <= 0:
        raise ValueError("弹簧丝直径必须为正数。")
    if params.helix_minor_radius <= 0:
        raise ValueError("弹簧丝半径不能大于或等于弹簧整体包络半径。")
    if params.coil_count < 3:
        raise ValueError("环向弹簧圈数过少，无法形成环形螺旋弹簧。")
    if not 0 < params.open_angle <= 3:
        raise ValueError("开口角度应大于 0° 且不超过 3°。")
    if params.points_per_coil < 8:
        raise ValueError("每圈离散点数建议不小于 8。")
    if params.sample_count < 2500:
        raise ValueError("中心线采样点数量应至少为 2500，以提高 STEP 几何稳定性。")

    # 粗略避免相邻螺旋圈之间自相交：环向每圈推进距离应明显大于弹簧丝直径。
    circumferential_pitch = 2 * pi * params.envelope_center_radius / params.coil_count
    if circumferential_pitch <= params.wire_diameter * 2.5:
        raise ValueError("coil_count 过大或 wire_diameter 过粗，可能造成局部自相交。")
    return params


def spring_centerline_points(params: SpringRingParameters) -> list[tuple[float, float, float]]:
    """用开口参数方程生成首尾不闭合的环形螺旋中心线。"""
    params = validate_parameters(params)
    points: list[tuple[float, float, float]] = []
    theta_end = 2 * pi - radians(params.open_angle)

    for index in range(params.sample_count + 1):
        theta = theta_end * index / params.sample_count
        phase = params.coil_count * theta

        # 中心线径向起伏：决定弹簧整体内外包络。
        radial_radius = params.envelope_center_radius + params.helix_minor_radius * cos(phase)

        # 中心线轴向起伏：与径向起伏相差 90°，形成紧凑的环形螺旋弹簧。
        z = params.helix_minor_radius * sin(phase)

        points.append((radial_radius * cos(theta), radial_radius * sin(theta), z))

    return points


def _profile_plane_at_path_start(points: list[tuple[float, float, float]]) -> Plane:
    """创建经过中心线起点且垂直于起点切向的扫掠截面平面。"""
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
    """创建单个微开口 clean 版环形螺旋弹簧 solid 实体。"""
    params = validate_parameters(params)
    points = spring_centerline_points(params)

    # 不再使用 periodic=True，也不再强制首尾闭合。
    # 微小开口可避免完全闭合扫掠在接缝处产生无效面片或缝合错误。
    path = cq.Workplane("XY").spline(points)
    profile_plane = _profile_plane_at_path_start(points)

    spring = (
        cq.Workplane(profile_plane)
        .circle(params.wire_radius)
        .sweep(path, isFrenet=True, clean=True)
        .clean()
    )
    return spring


def validate_solid(model: cq.Workplane) -> bool:
    """检查 CadQuery 结果是否为有效 solid；无效时返回 False 并打印提示。"""
    shape = model.val()
    shape_type = getattr(shape, "ShapeType", lambda: type(shape).__name__)()
    is_valid = bool(shape.isValid()) if hasattr(shape, "isValid") else True
    solid_count = len(model.solids().vals())

    print(f"CadQuery 形状类型：{shape_type}")
    print(f"Solid 数量：{solid_count}")
    print(f"几何有效性 isValid：{is_valid}")

    if solid_count != 1:
        print("警告：模型不是单个 solid，建议检查扫掠路径或截面。")
        return False
    if not is_valid:
        print("警告：CadQuery 判断该 solid 无效，将尝试下一组 open_angle/coil_count。")
        return False
    return True


def export_step(model: cq.Workplane, output_path: str | Path) -> Path:
    """导出 STEP 文件，供 COMSOL 或其他 CAE/CAD 软件导入。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(path))
    return path


def candidate_parameters(base_params: SpringRingParameters) -> Iterable[SpringRingParameters]:
    """按稳定性优先级生成自动尝试的开口角度和圈数组合。"""
    attempts = (
        (base_params.open_angle, base_params.coil_count),
        (2.0, base_params.coil_count),
        (3.0, base_params.coil_count),
        (3.0, 50),
        (3.0, 40),
    )
    seen: set[tuple[float, int]] = set()
    for open_angle, coil_count in attempts:
        key = (open_angle, coil_count)
        if key in seen:
            continue
        seen.add(key)
        yield replace(base_params, open_angle=open_angle, coil_count=coil_count)


def build_valid_spring(base_params: SpringRingParameters) -> tuple[cq.Workplane, SpringRingParameters]:
    """自动尝试不同 open_angle 和 coil_count，返回第一个有效弹簧实体。"""
    last_error: Exception | None = None
    for params in candidate_parameters(base_params):
        print("=" * 72)
        print(
            "尝试生成弹簧："
            f"open_angle={params.open_angle:.1f}°, "
            f"coil_count={params.coil_count}, "
            f"wire_diameter={params.wire_diameter:.3f} mm, "
            f"sample_points={params.sample_count + 1}"
        )
        try:
            model = make_single_spring_ring(params)
        except Exception as exc:  # CadQuery 几何构造错误时继续尝试下一组参数。
            last_error = exc
            print(f"生成失败：{exc}")
            continue
        if validate_solid(model):
            return model, params

    raise RuntimeError(
        "所有 open_angle/coil_count 组合均未生成有效弹簧实体，"
        "请进一步降低 coil_count 或 wire_diameter 后重试。"
    ) from last_error


def main() -> None:
    """脚本入口：生成 1 个微开口 clean 版弹簧本体并导出 STEP 文件。"""
    base_params = SpringRingParameters(
        # 可在此处修改弹簧本体尺寸、密度、默认开口角度和输出文件名。
        envelope_center_radius=18.82,
        envelope_radius=0.87,
        wire_diameter=0.15,
        coil_count=60,
        open_angle=1.0,
        points_per_coil=64,
        step_output_path="outputs/spring_ring_single_open_clean.step",
    )
    model, used_params = build_valid_spring(base_params)
    output = export_step(model, used_params.step_output_path)

    print("=" * 72)
    print("STEP 文件已导出")
    print(f"采用 open_angle = {used_params.open_angle:.1f}°")
    print(f"采用 coil_count = {used_params.coil_count}")
    print(f"采用 wire_diameter = {used_params.wire_diameter:.3f} mm")
    print(f"STEP 文件路径 = {output.resolve()}")
    print(f"中心线采样点数 = {used_params.sample_count + 1}")
    print(f"弹簧外侧最大半径 = {used_params.outer_radius:.3f} mm")
    print(f"弹簧内侧最小半径 = {used_params.inner_radius:.3f} mm")


if __name__ == "__main__":
    main()
