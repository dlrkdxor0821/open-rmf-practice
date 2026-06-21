# libi_rmf_bringup  ─ ⑤ launch 조립 (M2~)

- **빌드타입**: `ament_cmake` · **위치**: `fleet/src/libi_rmf_bringup`
- **rmf_demos 대응**: `rmf_demos` / `rmf_demos_gz`
- **역할**: RMF 코어 + fleet adapter + 시뮬/실물을 하나의 launch로 묶는다.

## 들어갈 것
```
launch/
  sim.launch.xml             ← Gazebo 시뮬 + RMF + adapter (slotcar, M2~M4)
  real.launch.xml            ← 실물 + domain_bridge + RMF (nav2, M5)
  include/
    common.launch.xml        ← RMF 코어 / nav graph 공통부
config/
```

## 단계별 launch
| 모듈 | launch | 내용 |
|---|---|---|
| M2~M4 | `sim.launch.xml` | slotcar 시뮬 1대~다중 + 태스크 |
| M5 | `real.launch.xml` | nav2 실로봇 + `libi_rmf_bridge` + RMF 코어 |

> 공통부(`common.launch.xml`)는 sim/real 둘 다 include → RMF 코어·nav graph·태스크 재사용.
