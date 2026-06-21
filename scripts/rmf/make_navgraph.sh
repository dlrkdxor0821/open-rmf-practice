#!/usr/bin/env bash
# building.yaml -> navgraph 생성 + (pairs 주면) 좌표 보정까지 한 번에.
#
# 사용법:
#   ① 좌표만 보기 :  ./make_navgraph.sh new_map.building.yaml
#   ② 보정+저장  :  ./make_navgraph.sh new_map.building.yaml new_map.pairs.yaml
#
# 보정 결과는 building.yaml 옆에 <이름>.navgraph.yaml 로 저장된다.
# (예: new_map.building.yaml -> new_map.navgraph.yaml)
# 다른 경로로 저장하려면: OUT_FILE=./foo.yaml ./make_navgraph.sh ...
#
# building.yaml 은 편집용 원본이라 건드리지 않는다. navgraph 는 파생물이므로
# building.yaml / pairs.yaml 이 바뀌면 다시 실행하면 된다.
set -e

BUILDING="$1"
PAIRS="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$BUILDING" ]; then
  echo "사용법: $0 <building.yaml> [pairs.yaml]"
  exit 1
fi

BUILDING_DIR="$(cd "$(dirname "$BUILDING")" && pwd)"
BUILDING_FILE="$(basename "$BUILDING")"
BASE="$(basename "$BUILDING" .building.yaml)"
OUT_FILE="${OUT_FILE:-$BUILDING_DIR/$BASE.navgraph.yaml}"

# 중간 산출물(building_map_generator 는 0.yaml 로 이름 강제)은 임시 폴더에
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# building.yaml 폴더에서 실행 → 레이어 png 자동 인식
( cd "$BUILDING_DIR" && ros2 run rmf_building_map_tools building_map_generator nav "$BUILDING_FILE" "$TMP" )
NAV="$TMP/0.yaml"

echo ""
echo "===== navgraph 좌표 (보정 전) ====="
python3 -c "import yaml; d=yaml.safe_load(open('$NAV')); [print(f'  ({v[0]:8.3f}, {v[1]:8.3f})') for v in d['levels']['L1']['vertices']]"

if [ -n "$PAIRS" ]; then
  echo ""
  python3 "$SCRIPT_DIR/fix_navgraph.py" "$NAV" "$PAIRS" -o "$OUT_FILE"
else
  echo ""
  echo "→ 위 좌표로 pairs.yaml 작성 후 다시 실행하면 보정+저장됨:"
  echo "   $0 $BUILDING <pairs.yaml>   (저장 위치: $OUT_FILE)"
fi
