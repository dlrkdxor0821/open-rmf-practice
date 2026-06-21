# libi_rmf_maps  ─ ① 지도 (M1)

- **빌드타입**: `ament_cmake` · **위치**: `fleet/src/libi_rmf_maps`
- **rmf_demos 대응**: `rmf_demos_maps` (또는 `rosconkr_maps`)
- **역할**: traffic_editor `building.yaml`(★원본·손관리) 보관 + 빌드 시 `building_map_generator`로
  `world` / `nav graph` **파생물 생성**.

## 들어갈 것 — `maps/library/` 4-파일 구성

맵 한 장소의 모든 표현(격자/배경/RMF지도)을 **한 폴더에 모아 단일 출처**로 둔다.
pgm·yaml도 pinky가 아니라 **여기**에 둔다 (코드 수정 ↔ 맵 데이터 분리). nav2는 이 경로를 *참조*만 함.

```
fleet/src/libi_rmf_maps/maps/library/
  library.pgm            ← SLAM 점유격자
  library.yaml           ← pgm 메타(원점·해상도)
  library.png            ← pgm→png 배경
  library.building.yaml  ← RMF 지도 본체 (차선·노드·벽)
CMakeLists.txt           ← (예정) 빌드 시 world/nav graph 자동 생성
package.xml              ← (예정)
```

| 파일 | 누가 쓰나 | 언제 |
|---|---|---|
| `library.pgm` | `pgm_to_gazebo`(world 생성) + nav2 `map_server` | M1, M5 |
| `library.yaml` | 좌표 정렬 기준(원점·해상도) + nav2 `map_server` | M1, M5 |
| `library.png` | traffic_editor 배경(트레이싱 종이) | M1 (편집용) |
| `library.building.yaml` | RMF 본체 — `building_map_generator`로 world/navgraph 생성 | M1~ |

> ⚠️ `pgm → png → building.yaml`은 같은 장소를 묘사하는 **한 세트**라 반드시 같이 둔다 (떼면 좌표 드리프트).
> ⚠️ **world.sdf·nav graph는 여기 두지 않음** — building.yaml로부터 빌드 때 생성되는 파생물(build/install로 빠짐). 소스엔 위 4개만.

### nav2(M5)는 복사 말고 참조
pinky 기존 샘플 맵(`pinky_navigation/map`)은 그대로 두고, ABA library 맵은 경로만 덮어쓴다:
```xml
<!-- libi_drive 오버레이 / bringup launch -->
<arg name="map" value="$(find-pkg-share libi_rmf_maps)/maps/library/library.yaml"/>
```
> `controller/`와 `fleet/`는 별도 colcon ws → nav2가 참조하려면 **두 ws를 같이 source(overlay)**. (M5는 어차피 둘 다 띄움)

## 생성 명령 (참고 — open-rmf-test/README 4장)
```bash
# world (Gazebo 화면)        : <입력.yaml> <출력.world> <모델출력폴더>
ros2 run rmf_building_map_tools building_map_generator gazebo library.building.yaml library.world .
# nav graph (RMF 주행/교통)  : <입력.yaml> <출력폴더>   → 0.yaml, 1.yaml ...
ros2 run rmf_building_map_tools building_map_generator nav    library.building.yaml .
```

> ⚠️ nav graph는 building.yaml에 **lane(차선)** 이 있어야 나온다. 벽만 있으면 빈 그래프.
> ⚠️ `pgm_to_gazebo` world ↔ 이 nav graph의 **좌표 정렬** 검증 필수 (docs/study-plan.md §5·6).
