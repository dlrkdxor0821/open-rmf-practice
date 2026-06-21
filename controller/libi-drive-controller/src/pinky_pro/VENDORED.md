# pinky_pro (외부 코드 기반 — 우리가 fork해서 직접 수정)

- **출처**: https://github.com/pinklab-art/pinky_pro (origin commit `d576618` 기준)
- **라이선스**: Apache-2.0 (이 디렉터리의 `LICENSE` 동봉 = 출처표기 충족)
- **가져온 방식**: 전체 복사 (`.git`·빌드산출물 제외). 실물 로봇까지 사용 예정이라 전 패키지 포함.

## 규칙
- **이 패키지는 직접 수정해도 된다.** RMF·실물 커스터마이즈를 위해 **fork로 운용**한다. (이전의 "직접 수정 금지" 규칙은 폐기)
- (라이선스) Apache-2.0이므로 `LICENSE`는 유지하고, 파일을 크게 고치면 헤더에 변경 사실을 한 줄 남기는 정도면 충분하다. (§4(b)는 *배포* 시점 의무이며 학습 단계에선 권고)
- 업스트림 최신본이 필요해지면 그때 이 복사본과 비교/병합한다. (submodule 전환은 선택사항 — 강제 아님)
- 단, **맵 같은 우리 프로젝트 데이터는 여전히 이 폴더가 아니라 `fleet/src/libi_rmf_maps`에 둔다** (코드 수정과 데이터 분리).

## 패키지 RMF 관련도 (요약)
| 관련도 | 패키지 |
|---|---|
| 시뮬 now (M2~M4) | `pinky_description`(URDF/메시), `pinky_gz_sim`(gz spawn/bridge/world) |
| M5 (실 nav2) | `pinky_navigation` |
| RMF 무관 (실HW) | `pinky_bringup`, `pinky_interfaces`, `pinky_lamp_control`, `pinky_led`, `pinky_emotion`, `pinky_imu_bno055`, `pinky_sensor_adc` |

> 시뮬(M2~M4)에서 RMF는 **slotcar**로 구동하므로 diff-drive 대신 주로 `pinky_description`의 **메시/링크(외형)** 를 사용. 실물(M5)에선 `pinky_navigation`(nav2) 전체가 필요.
