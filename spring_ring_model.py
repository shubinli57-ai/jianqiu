"""
生成单个 clean 版环形螺旋弹簧本体的 CadQuery 参数化模型。

模型目标：
- STEP 文件中只包含弹簧本体，不包含平台、外壳、环形槽或任何辅助实体；
- 弹簧环位于 XY 平面内，并围绕 Z 轴形成完整闭合圆环；
- 通过更细弹簧丝、较高中心线采样密度和导出前实体有效性检查，提高 COMSOL 导入稳定性。

坐标约定：
- Z 轴为弹簧环中心轴线；
- XY 平面为弹簧环中面；
- 弹簧外侧最大半径约为 envelope_center_radius + envelope_radius = 19.69 mm；
- 弹簧内侧最小半径约为 envelope_center_radius - envelope_radius = 17.95 mm。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin, sqrt
from pathlib import Path

import cadquery as cq
from cadquery import Plane


@dataclass(frozen=True)
class SpringRingParameters:
    """单个环形螺旋弹簧本体参数，长度单位均为 mm。"""

    # 弹簧整体包络中心半径：决定弹簧本体环形中心位置。
    envelope_center_radius: float = 18.82

    # 弹簧整体截面包络半径：不是弹簧丝半径；决定整体外/内包络尺寸。
    envelope_radius: float = 0.87

    # 弹簧丝直径：真实金属丝圆截面直径；建议 0.15 mm 或 0.18 mm。
    wire_diameter: float = 0.15

    # 环向弹簧圈数：小螺旋沿完整圆环绕行的圈数；建议 60 到 80。
    coil_count: int = 70

    # 每圈离散点数：默认 46，70 圈时中心线点数超过 3000，提高闭合和扫掠稳定性。
    points_per_coil: int = 46

    # STEP 文件输出路径：clean 版单个弹簧本体模型。
    step_output_path: str = "outputs/spring_ring_single_clean.step"

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
        """闭合中心线离散段数。"""
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
        raise ValueError("环向弹簧圈数过少，无法形成闭合环形螺旋弹簧。")
    if not 8 <= params.points_per_coil:
        raise ValueError("每圈离散点数建议不小于 8。")
    if params.sample_count < 3000:
        raise ValueError("中心线采样点数量应至少为 3000，以提高 STEP 几何稳定性。")

    # 粗略避免相邻螺旋圈之间自相交：环向每圈推进距离应明显大于弹簧丝直径。
    circumferential_pitch = 2 * pi * params.envelope_center_radius / params.coil_count
    if circumferential_pitch <= params.wire_diameter * 2.5:
        raise ValueError("coil_count 过大或 wire_diameter 过粗，可能造成局部自相交。")
    return params


def spring_centerline_points(params: SpringRingParameters) -> list[tuple[float, float, float]]:
    """用周期参数方程生成首尾位置和切向连续的闭合环形螺旋中心线。"""
    params = validate_parameters(params)
    points: list[tuple[float, float, float]] = []

    for index in range(params.sample_count + 1):
        theta = 2 * pi * index / params.sample_count
        phase = params.coil_count * theta

        # 中心线径向起伏：决定弹簧整体内外包络。
        radial_radius = params.envelope_center_radius + params.helix_minor_radius * cos(phase)

        # 中心线轴向起伏：与径向起伏相差 90°，形成真实的环形螺旋弹簧。
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
    """创建单个完整闭合的 clean 版环形螺旋弹簧 solid 实体。"""
    params = validate_parameters(params)
    points = spring_centerline_points(params)

    # points 首尾重合，用于校核闭合；建周期样条时去掉重复末点。
    # periodic=True 可保证首尾切向连续，避免闭合处出现折角或不稳定缝合面。
    path = cq.Workplane("XY").spline(points[:-1], periodic=True)
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
        print("警告：CadQuery 判断该 solid 无效，请降低 coil_count 或 wire_diameter 后重试。")
        return False
    return True


def export_step(model: cq.Workplane, output_path: str | Path) -> Path:
    """导出 STEP 文件，供 COMSOL 或其他 CAE/CAD 软件导入。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(model, str(path))
    return path


def main() -> None:
    """脚本入口：生成 1 个 clean 版标准弹簧本体并导出 STEP 文件。"""
    params = SpringRingParameters(
        # 可在此处修改弹簧本体尺寸、密度和输出文件名。
        envelope_center_radius=18.82,
        envelope_radius=0.87,
        wire_diameter=0.15,
        coil_count=70,
        points_per_coil=46,
        step_output_path="outputs/spring_ring_single_clean.step",
    )
    model = make_single_spring_ring(params)
    if not validate_solid(model):
        raise RuntimeError("生成的弹簧实体未通过有效性检查，已停止导出 STEP。")

    output = export_step(model, params.step_output_path)
    print(f"STEP 文件已导出：{output.resolve()}")
    print(f"中心线采样点数 = {params.sample_count + 1}")
    print(f"弹簧外侧最大半径 = {params.outer_radius:.3f} mm")
    print(f"弹簧内侧最小半径 = {params.inner_radius:.3f} mm")


if __name__ == "__main__":
    main()
