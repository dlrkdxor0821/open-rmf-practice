# libi_rmf_maps  ─ ① 지도 (M1)

- **빌드타입**: `ament_cmake` · **위치**: `fleet/src/libi_rmf_maps`
- **rmf_demos 대응**: `rmf_demos_maps` (또는 `rosconkr_maps`)
- **역할**: traffic_editor `building.yaml`(★원본·손관리) 보관 + 빌드 시 `building_map_generator`로
  `world` / `nav graph` **파생물 생성**.

## 들어갈 것
```
maps/library/
  library.building.yaml   ← traffic_editor 원본 (pgm 위에 차선 그린 결과)
  library.pgm + .yaml     ← SLAM 점유격자 (traffic_editor 배경 / pgm_to_gazebo 입력)
  library.png             ← pgm → png (traffic_editor 배경용)
CMakeLists.txt            ← (예정) 빌드 시 world/nav graph 자동 생성
package.xml               ← (예정)
```

## 생성 명령 (참고 — open-rmf-test/README 4장)
```bash
# world (Gazebo 화면)        : <입력.yaml> <출력.world> <모델출력폴더>
ros2 run rmf_building_map_tools building_map_generator gazebo library.building.yaml library.world .
# nav graph (RMF 주행/교통)  : <입력.yaml> <출력폴더>   → 0.yaml, 1.yaml ...
ros2 run rmf_building_map_tools building_map_generator nav    library.building.yaml .
```

> ⚠️ nav graph는 building.yaml에 **lane(차선)** 이 있어야 나온다. 벽만 있으면 빈 그래프.
> ⚠️ `pgm_to_gazebo` world ↔ 이 nav graph의 **좌표 정렬** 검증 필수 (docs/study-plan.md §5·6).
