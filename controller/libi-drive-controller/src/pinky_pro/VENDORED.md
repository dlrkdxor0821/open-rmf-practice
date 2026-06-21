# VENDORED — pinky_pro (그대로 복사된 외부 코드)

- **출처**: https://github.com/pinklab-art/pinky_pro (origin commit `d576618` 기준)
- **라이선스**: Apache-2.0 (이 디렉터리의 `LICENSE` 동봉 = 출처표기 충족)
- **가져온 방식**: 전체 복사 (`.git`·빌드산출물 제외). 실물 로봇까지 사용 예정이라 전 패키지 포함.

## ⚠️ 규칙
- **이 디렉터리는 vendor(외부 코드)다. 직접 수정하지 말 것.** 수정·RMF용 변경은 상위 `libi_drive/`(우리 overlay 패키지)에 둔다.
- 부득이 vendor 파일을 고치면 Apache-2.0 §4(b)에 따라 **변경된 파일에 "changed" 표시**를 남길 것.
- 업스트림 동기화가 필요해지면 이 복사본을 지우고 `git submodule add https://github.com/pinklab-art/pinky_pro.git` 로 전환.

## 패키지 RMF 관련도 (요약)
| 관련도 | 패키지 |
|---|---|
| 시뮬 now (M2~M4) | `pinky_description`(URDF/메시), `pinky_gz_sim`(gz spawn/bridge/world) |
| M5 (실 nav2) | `pinky_navigation` |
| RMF 무관 (실HW) | `pinky_bringup`, `pinky_interfaces`, `pinky_lamp_control`, `pinky_led`, `pinky_emotion`, `pinky_imu_bno055`, `pinky_sensor_adc` |

> 시뮬(M2~M4)에서 RMF는 **slotcar**로 구동하므로 diff-drive 대신 주로 `pinky_description`의 **메시/링크(외형)** 를 사용. 실물(M5)에선 `pinky_navigation`(nav2) 전체가 필요.
