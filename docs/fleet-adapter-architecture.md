# Fleet Adapter 구조: 독립적인 두 축 (fleet_manager · 도메인)

> **핵심 한 줄**
> "**fleet_manager가 필요한가**"와 "**도메인이 몇 개인가**"는 **서로 무관한 별개의 두 축**이다.
> 도메인 개수가 fleet_manager 존재 여부를 결정하지 **않는다.**

흔한 오해: *"namespace(단일 도메인)라서 fleet_manager가 필요 없다"* → ❌
정답: *"로봇이 **ROS2(nav2)** 라서 fleet_manager가 필요 없다"* → ✅ (namespace든 domain_bridge든 무관)

---

## TL;DR

| 축 | 질문 | **무엇이 결정하나** |
|---|---|---|
| **축1** | fleet_manager 있냐/없냐? | 로봇이 무슨 "언어"를 쓰냐 — **REST vs ROS2** |
| **축2** | bridge 있냐 (namespace vs domain_bridge)? | 도메인이 몇 개냐 — **1개 vs 여러개** |

두 축은 **독립** → 아래 4가지 조합이 모두 가능하다.

---

## 축1 — fleet_manager: 로봇의 "언어"가 결정

`fleet_manager` = adapter와 로봇 사이의 **통역사 / 중간 서버**(보통 REST). **항상 필요한 게 아니라 특정 조건에서만** 필요하다.

### fleet_manager가 **필요한** 경우 (정의)

**① 로봇이 REST/HTTP API만 제공** (ROS2를 안 열어줌) — 상용 로봇이 흔히 그럼.
adapter(ROS2)와 로봇(HTTP)의 언어가 달라 **통역사 필요**.
```
adapter → [HTTP REST] → fleet_manager → 로봇 자체 API
```

> **왜 상용 로봇은 ROS2를 안 쓰고 REST만 줄까?** (자주 헷갈리는 부분)
> - **내부가 ROS2가 아닐 수 있음** — 독자 SW·ROS1·커스텀 스택. 외부엔 REST 하나만 노출.
> - **내부 은닉 (IP 보호)** — 벤더는 자기 nav 스택·센서 구조를 안 보여주고 싶음. REST = 깔끔한 "계약", 내부 감춤.
> - **보안·네트워크** — ROS2(DDS)는 신뢰된 LAN 가정 + 수다스러움. 외부망에 그대로 열면 위험·과대역폭. REST/HTTPS는 방화벽 친화·인증 표준.
> - **안정성·버전** — REST는 고정 계약. 벤더가 내부를 바꿔도 통합이 안 깨짐 (ROS2 토픽/타입은 내부 구현에 강결합).
> - **언어 무관** — REST는 아무 언어/시스템에서 호출. ROS2는 ROS2 스택이 있어야 함.
>
> → 즉 **"남이 만든(상용) 로봇"** 은 보통 REST만 준다. 반면 **우리 pinky는 우리가 만든 ROS2 로봇**이라 nav2를 직접 열 수 있어 통역사가 불필요.

**② 외부 FMS — 여러 벤더(이기종)를 하나의 통일 API로 추상화**할 때 (선택적 편의).
서로 다른 벤더 로봇들을 **하나의 fleet_manager/FMS 뒤로** 숨기면, RMF는 **API 하나만** 상대 → 벤더를 추가해도 RMF 쪽은 안 건드림.
> 예: A사 배달봇 + B사 청소봇 + C사 안내봇 → **FMS가 통일 API 제공** → RMF는 그 FMS 하나와만 통신.
> *(※ 필수 아님 — 각 타입이 ROS2면 "타입마다 adapter"로도 충분. FMS는 "통합을 단순화하고 싶을 때"의 편의/선택.)*

### fleet_manager가 **불필요한** 경우
- **로봇이 ROS2 네이티브** (nav2 = ROS2 액션) → adapter도 ROS2 → **같은 언어** → 통역사 없이 **직접 호출**.
  ```
  adapter(RobotClientAPI) → [ROS2 action: NavigateToPose] → nav2
  ```
- **이기종이어도 모두 ROS2면** → **타입마다 fleet_adapter**(N개)로 직접. manager를 끼우면 `ROS2→REST→ROS2` 군더더기.

**우리 pinky = nav2(ROS2) · 단일 타입** → **fleet_manager 불필요 → 뺀다.**
(rmf_demos 템플릿은 "로봇이 REST API를 준다"고 가정해 fleet_manager가 들어있던 것 — 우리 경우엔 괜한 중간층이라 제거.)

---

## 축2 — 도메인 구성: 로봇 격리 여부가 결정

여러 로봇을 하나의 RMF로 묶을 때, 토픽을 어떻게 조직하나.

- **단일 도메인 + namespace**
  모든 로봇 + RMF가 **한 ROS 그래프**. `pinky1/...`, `pinky2/...` prefix로 구분. bridge 불필요.

- **도메인 분리 + domain_bridge**
  로봇마다 **자기 도메인(격리)**. `domain_bridge`가 RMF에 필요한 토픽만 도메인 사이로 옮김.
  ```
  [ 로봇1 도메인 (ID=1) ]                      [ RMF 도메인 (ID=0) ]
    pinky1 nav2:                                rmf_traffic_schedule
      /navigate_to_pose ◄──┐              ┌──►  fleet_adapter (두뇌)
      /amcl_pose        ───┤ domain_bridge├──►  dispatcher
      /cmd_vel /battery    └─(필요 토픽만)─┘
  [ 로봇2 도메인 (ID=2) ]
    pinky2 nav2: ... ◄────  domain_bridge  ────►
  ```

| | 단일 도메인 (namespace) | 도메인 분리 (domain_bridge) |
|---|---|---|
| 장점 | **단순**, 추가 프로세스 없음, 셋업 쉬움 | 로봇 내부 토픽 격리, 이름충돌 없음, 분산배포·확장 좋음 |
| 단점 | 한 네트워크/도메인 공유 필수 | bridge 설정·프로세스 추가(복잡) |
| 적합 | **sim**, 같은 네트워크 소수 로봇 | **실 분산 로봇 fleet** |

> **중요:** domain_bridge는 fleet_adapter를 **대체하지 않는다.** fleet_adapter(두뇌)는 항상 있고,
> domain_bridge는 그 **밑에서 토픽을 운반**하는 배관일 뿐. 어댑터 입장에선 토픽이 같은 도메인에 있든
> bridge가 날라준 거든 **똑같이 보인다(투명)** → 어댑터 코드는 namespace든 domain_bridge든 거의 동일.

---

## ★ 두 축은 독립 — 4가지 조합

도메인 개수(축2)가 fleet_manager(축1)를 결정하지 **않는다.** 따로 정한다.

| 로봇 언어 (축1) | 도메인 (축2) | fleet_manager | bridge | 예시 |
|---|---|---|---|---|
| **ROS2 (nav2)** | 단일 | ❌ 없음 | namespace | **rosconkr** (ROSCon 데모) |
| **ROS2 (nav2)** | 분리 | ❌ 없음 | **domain_bridge** | **★ 우리 M5 (ABA)** |
| REST API | 단일 | ✅ 있음 | namespace | 상용로봇, 한 네트워크 |
| REST API | 분리 | ✅ 있음 | domain_bridge | 상용로봇, 분산 배포 |

→ **두 번째 줄**처럼 **fleet_manager 없음(❌) + domain_bridge 있음(✅)** 이 동시에 성립한다.
이게 가능한 이유 = **두 축이 무관**하기 때문.

---

## 우리(ABA / libi) 선택 — 확정

- **축1 → fleet_manager 없음 (제거 확정).** pinky = nav2(ROS2) · 단일 타입이라 통역사 불필요.
  `RobotClientAPI`가 nav2를 직접 호출(= "방법2", rosconkr식). M2~M4의 fleet_manager(슬롯카용)는 **M5에서 뺀다.**
- **축2 → 다중로봇 제어 = `domain_bridge` (확정).** 로봇별 도메인 격리(학습 + 실배포 대비). `libi_rmf_bridge`에 구현.

> **M5 = fleet_manager 없음(ROS2·단일타입) + domain_bridge 있음(도메인 분리).**

| 단계 | 내용 | 두 축과의 관계 |
|---|---|---|
| M5a | nav2가 우리 맵에서 diffdrive pinky 주행 | (단일 로봇, 도메인 얘기 전) |
| M5b | `fleet_adapter` (nav2 직접) | **축1 = fleet_manager 없음** 확정 |
| M5c | `libi_rmf_bridge` (domain_bridge) | **축2 = 도메인 분리** 채택 |

---

## 참고
- 어댑터 백엔드 레퍼런스: `~/rosconkr_rmf/rosconkr_pinky_fleet_adapter` (pinky + nav2 + EasyFullControl, fleet_manager 없음 / namespace)
- 패키지 역할 비교: [`rmf_packages.html`](rmf_packages.html) / `.pdf`
- 학습 사다리: [`study-plan.md`](study-plan.md)
