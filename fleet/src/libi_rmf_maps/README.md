# libi_rmf_maps  ─ ① 지도 (M1)

- **빌드타입**: `ament_cmake` · **위치**: `fleet/src/libi_rmf_maps`
- **rmf_demos 대응**: `rmf_demos_maps` (또는 `rosconkr_maps`)
- **역할**: 맵 원본(traffic_editor `building.yaml` 등) 보관 + navgraph(RMF 주행 그래프) 생성·보정.
  보정 **워크플로우/도구는 루트 README의 "M1 맵 작업" 섹션**(`scripts/rmf/`) 참고.
- `CMakeLists.txt`/`package.xml` 은 아직 미작성 — M2에서 빌드 연동 시 추가.

## maps/library/ 파일 구성

맵 한 장소의 모든 표현을 한 폴더에 모아 **단일 출처**로 둔다. pgm·png도 pinky가 아니라 여기에 둔다.

```
fleet/src/libi_rmf_maps/maps/library/
  # ── 원본 (소스, 손관리) ──
  new_map.pgm            ← SLAM 점유격자
  new_map.yaml           ← pgm 메타(원점·해상도) — 좌표 정렬 기준
  new_map.png            ← pgm→png 배경 (traffic_editor 트레이싱 + dst용 점 찍기)
  new_map.building.yaml  ← RMF 지도 본체 (vertex·lane·measurement) — traffic_editor 편집
  new_map.pairs.yaml     ← navgraph 보정용 대응점 (src=navgraph / dst=rviz 클릭)
  # ── 헬퍼 ──
  new_map.png.yaml       ← png를 rviz map으로 띄우는 yaml (점 보며 dst 읽기용; new_map.yaml과 origin/res 동일)
  # ── 파생물 (make_navgraph.sh 출력) ──
  new_map.navgraph.yaml  ← 보정된 RMF 주행 그래프 (building.yaml + pairs.yaml 로 재생성 가능)
```

> 가제보 world(`new_map.sdf`)는 `controller/.../pinky_gz_sim/worlds/` 에 있다 (gz 패키지가 자연스러운 위치, pgm_to_gazebo 생성).

| 파일 | 종류 | 누가 쓰나 |
|---|---|---|
| `new_map.pgm` / `.yaml` | 원본 | pgm_to_gazebo(world), nav2 map_server, 좌표 정렬 기준 |
| `new_map.png` | 원본 | traffic_editor 배경, dst용 점 찍기 |
| `new_map.building.yaml` | 원본 | RMF 지도 본체 (traffic_editor 편집) |
| `new_map.pairs.yaml` | 원본 | navgraph 보정 대응점 |
| `new_map.png.yaml` | 헬퍼 | rviz에서 png 띄워 dst 읽기 |
| `new_map.navgraph.yaml` | 파생물 | RMF 주행 그래프 (fleet adapter가 읽음, M2~) |

> ⚠️ `pgm → png → building.yaml`은 같은 장소를 묘사하는 **한 세트**라 반드시 같이 둔다 (떼면 좌표 드리프트).

## navgraph 생성·보정 (요약 — 상세는 루트 README)

```bash
# building.yaml + pairs.yaml → new_map.navgraph.yaml (생성 + 좌표 보정)
scripts/rmf/make_navgraph.sh maps/library/new_map.building.yaml maps/library/new_map.pairs.yaml
```
- ⚠️ navgraph는 building.yaml에 **lane(차선)** 이 있어야 나온다. vertex만 있으면 연결 안 됨.
- ⚠️ world(pgm 기준) ↔ navgraph(building.yaml 기준)는 출처가 달라 어긋남 → `pairs`로 **scale·회전·이동 보정** (M1 핵심 함정, docs/study-plan.md §5·6).
- navgraph는 **파생물** — building.yaml/pairs.yaml 바뀌면 재생성. building.yaml(편집용 원본)은 안 건드림.

## nav2(M5)는 복사 말고 참조
ABA library 맵 경로를 nav2 launch에서 **참조만** 한다 (복사 X):
```xml
<arg name="map" value="$(find-pkg-share libi_rmf_maps)/maps/library/new_map.yaml"/>
```
> `controller/`와 `fleet/`는 별도 colcon ws → nav2가 참조하려면 **두 ws를 같이 source(overlay)**. (M5는 어차피 둘 다 띄움)
