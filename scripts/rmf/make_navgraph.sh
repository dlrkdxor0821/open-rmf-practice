#!/usr/bin/env bash
# building.yaml -> navgraph 생성 + (pairs 주면) 좌표 보정까지 한 번에.
#
# 사용법:
#   ① 좌표만 보기 :  ./make_navgraph.sh new_map.building.yaml
#   ② 보정까지   :  ./make_navgraph.sh new_map.building.yaml pairs.yaml
#
# 출력 위치는 기본 /tmp/out. 바꾸려면 OUT=./out ./make_navgraph.sh ...
set -e

BUILDING="$1"
PAIRS="$2"
OUT="${OUT:-/tmp/out}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$BUILDING" ]; then
  echo "사용법: $0 <building.yaml> [pairs.yaml]"
  exit 1
fi

# 경로 절대화 (어디서 실행해도 png 가 building.yaml 옆에서 잡히도록)
BUILDING_DIR="$(cd "$(dirname "$BUILDING")" && pwd)"
BUILDING_FILE="$(basename "$BUILDING")"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"

# 1) navgraph 생성 (building.yaml 폴더에서 실행 → 레이어 png 자동 인식)
( cd "$BUILDING_DIR" && ros2 run rmf_building_map_tools building_map_generator nav "$BUILDING_FILE" "$OUT" )
NAV="$OUT/0.yaml"

# 2) 좌표 출력
echo ""
echo "===== navgraph 좌표 ($NAV) ====="
python3 -c "import yaml; d=yaml.safe_load(open('$NAV')); [print(f'  ({v[0]:8.3f}, {v[1]:8.3f})') for v in d['levels']['L1']['vertices']]"

# 3) pairs 있으면 보정, 없으면 안내
if [ -n "$PAIRS" ]; then
  echo ""
  python3 "$SCRIPT_DIR/fix_navgraph.py" "$NAV" "$PAIRS" -o "$OUT/0_fixed.yaml"
else
  echo ""
  echo "→ 위 좌표로 pairs.yaml 작성 후 다시 실행하면 보정까지 됨:"
  echo "   $0 $BUILDING pairs.yaml"
fi
