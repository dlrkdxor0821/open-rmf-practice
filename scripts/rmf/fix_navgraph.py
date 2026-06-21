#!/usr/bin/env python3
"""navgraph 좌표 보정 스크립트 (대응점 기반 2D 닮음변환).

building_map_generator 로 만든 nav graph 의 좌표가 가제보(pgm_to_gazebo) world 와
어긋날 때 사용한다. 대응점 몇 쌍을 주면 scale·회전·이동(2D similarity)을
최소제곱으로 구해 nav graph 의 모든 좌표(vertex, door endpoint)에 적용한다.

  dst ≈ scale * R(θ) * src + t      (R 은 회전, 반사는 없음)

사용법:
    python fix_navgraph.py <navgraph.yaml> <pairs.yaml> [-o out.yaml] [--dry-run]

pairs.yaml 형식 (pairs.example.yaml 참고):
    - src: [10.0, -8.0]      # 현재(틀린) navgraph 좌표
      dst: [-5.929, 14.567]  # 가제보에서 있어야 할 실좌표
    - src: [...]
      dst: [...]

대응점 얻는 법:
    - src: rviz 에서 navgraph waypoint 가 떠 있는 (잘못된) 좌표
    - dst: 가제보/pgm 맵에서 그 점이 실제로 있어야 할 좌표
    최소 2쌍, 서로 멀리 떨어진 점일수록 정확. 3쌍 이상이면 오차가 평균화됨.

참고: 이 스크립트는 회전+등배스케일+이동만 다룬다(반사 X). y축이 뒤집힌
경우엔 RMS 잔차가 크게 나오는데, 보통 building_map_generator 가 y-flip 을
ROS 좌표계로 맞춰주므로 정상 파이프라인에선 발생하지 않는다.
"""
import argparse
import math
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML 필요: pip install pyyaml (또는 ROS 환경 source)")


def load_pairs(path):
    """대응점 yaml 을 [(src, dst), ...] 로 읽는다. 최상위 리스트 / pairs: 키 둘 다 허용."""
    with open(path) as f:
        data = yaml.safe_load(f)
    if isinstance(data, dict) and "pairs" in data:
        data = data["pairs"]
    pairs = []
    for p in data:
        src = tuple(float(v) for v in p["src"])
        dst = tuple(float(v) for v in p["dst"])
        pairs.append((src, dst))
    return pairs


def solve_similarity(pairs):
    """dst ≈ s*R*src + t 를 최소제곱으로 푼다 (닫힌 해, 반사 없음).

    c = s*cosθ, d = s*sinθ 로 두면 선형이라 SVD 없이 바로 풀린다.
    반환: (scale, theta_rad, tx, ty)
    """
    n = len(pairs)
    mu_sx = sum(s[0] for s, _ in pairs) / n   # src 무게중심
    mu_sy = sum(s[1] for s, _ in pairs) / n
    mu_dx = sum(d[0] for _, d in pairs) / n   # dst 무게중심
    mu_dy = sum(d[1] for _, d in pairs) / n

    A = B = W = 0.0
    for (sx, sy), (dx, dy) in pairs:
        sxc, syc = sx - mu_sx, sy - mu_sy
        dxc, dyc = dx - mu_dx, dy - mu_dy
        A += sxc * dxc + syc * dyc      # cos 성분 (내적 합)
        B += sxc * dyc - syc * dxc      # sin 성분 (외적 합)
        W += sxc * sxc + syc * syc      # src 분산 합

    if W == 0.0:
        sys.exit("대응점의 src 가 한 점에 모여 있어 변환을 풀 수 없음 "
                 "(서로 떨어진 점 2개 이상 필요)")

    c = A / W   # s*cosθ
    d = B / W   # s*sinθ
    scale = math.hypot(c, d)
    theta = math.atan2(d, c)
    tx = mu_dx - (c * mu_sx - d * mu_sy)   # t = mu_d - s*R*mu_s
    ty = mu_dy - (d * mu_sx + c * mu_sy)
    return scale, theta, tx, ty


def make_transform(scale, theta, tx, ty):
    """(x, y) -> (x', y') 변환 함수를 만든다."""
    c = scale * math.cos(theta)
    d = scale * math.sin(theta)

    def tf(x, y):
        return (c * x - d * y + tx, d * x + c * y + ty)

    return tf


def rms_residual(pairs, tf):
    """변환 후 대응점이 얼마나 잘 맞는지(RMS, 점별 오차) 계산한다."""
    total = 0.0
    rows = []
    for (sx, sy), (dx, dy) in pairs:
        px, py = tf(sx, sy)
        err = math.hypot(px - dx, py - dy)
        total += err * err
        rows.append(((sx, sy), (dx, dy), (px, py), err))
    return math.sqrt(total / len(pairs)), rows


def apply_to_navgraph(data, tf):
    """navgraph 데이터의 모든 좌표에 변환을 in-place 로 적용. (vertex, door endpoint)"""
    n_v = n_d = 0
    for level in (data.get("levels") or {}).values():
        for v in level.get("vertices", []):
            v[0], v[1] = tf(v[0], v[1])
            n_v += 1
    for door in (data.get("doors") or {}).values():
        for ep in door.get("endpoints", []):
            ep[0], ep[1] = tf(ep[0], ep[1])
            n_d += 1
    lifts = data.get("lifts") or {}
    if lifts:
        print(f"  ⚠️  lifts {len(lifts)}개 발견 — 리프트 좌표는 자동 변환하지 않음(수동 확인 필요)")
    return n_v, n_d


def _default_out(path):
    if path.endswith(".yaml"):
        return path[:-5] + "_fixed.yaml"
    return path + "_fixed.yaml"


def main():
    ap = argparse.ArgumentParser(
        description="navgraph 좌표 보정 (대응점 기반 2D 닮음변환)")
    ap.add_argument("navgraph", help="building_map_generator 가 만든 nav graph yaml")
    ap.add_argument("pairs", help="대응점 yaml (src→dst)")
    ap.add_argument("-o", "--output", help="출력 경로 (기본: <navgraph>_fixed.yaml)")
    ap.add_argument("--dry-run", action="store_true",
                    help="변환만 계산·출력하고 파일은 저장하지 않음")
    args = ap.parse_args()

    pairs = load_pairs(args.pairs)
    if len(pairs) < 2:
        sys.exit(f"대응점이 최소 2쌍 필요 (지금 {len(pairs)}쌍)")

    scale, theta, tx, ty = solve_similarity(pairs)
    tf = make_transform(scale, theta, tx, ty)
    rms, rows = rms_residual(pairs, tf)

    print("=== 변환 계산 결과 ===")
    print(f"  대응점     : {len(pairs)}쌍")
    print(f"  scale      : {scale:.6f}")
    print(f"  rotation   : {math.degrees(theta):+.3f}°")
    print(f"  offset     : ({tx:+.4f}, {ty:+.4f})")
    print(f"  RMS 잔차   : {rms:.4f} m   (작을수록 잘 맞음)")
    print("  --- 점별 잔차 ---")
    for (s, dgt, p, err) in rows:
        s_r = tuple(round(v, 3) for v in s)
        p_r = tuple(round(v, 3) for v in p)
        d_r = tuple(round(v, 3) for v in dgt)
        print(f"    src{s_r} → {p_r}  (목표 {d_r}, 오차 {err:.4f} m)")

    if args.dry_run:
        print("\n(--dry-run: 파일 미저장)")
        return

    with open(args.navgraph) as f:
        data = yaml.safe_load(f)
    n_v, n_d = apply_to_navgraph(data, tf)

    out = args.output or _default_out(args.navgraph)
    with open(out, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False,
                       default_flow_style=None, allow_unicode=True)

    print(f"\n  변환 적용: vertex {n_v}개, door endpoint {n_d}개")
    print(f"  저장: {out}")


if __name__ == "__main__":
    main()
