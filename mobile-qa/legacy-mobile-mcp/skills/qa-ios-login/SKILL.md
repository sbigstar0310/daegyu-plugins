---
name: qa-ios-login
description: iOS 시뮬레이터에서 React Native / Expo 앱의 이메일+비밀번호 로그인을 탐색 없이 결정적으로 수행한다. iOS 좌표계 변환 규칙, mobile_type_keys 글자 누락 회피, secureTextEntry 필드(WDA 미노출) 대응 절차를 포함한다. iOS QA 중 로그인이 필요하다고 판정됐을 때 사용한다.
when_to_use: iOS 시뮬레이터에서 앱에 로그인해야 할 때, 비밀번호 입력이 안 먹힐 때, 탭이 엉뚱한 곳에 들어갈 때, mobile_type_keys가 글자를 빠뜨릴 때.
---

# iOS 로그인 — 결정적 절차

**탐색하지 마라.** 이 절차는 이미 실기 검증된 것이다. 순서대로만 실행한다.

**전제**: `qa-preflight`로 앱이 실행 중이고 **로그인이 필요하다고 판정된 상태**여야 한다.
이미 로그인되어 있으면 이 스킬 전체를 건너뛴다.

---

## 입력값 (전부 설정에서, 추측 금지)

| 값 | 출처 |
| --- | --- |
| 이메일 필드 testID | `auth.testIds.email` |
| 비밀번호 필드 testID | `auth.testIds.password` |
| 제출 버튼 testID | `auth.testIds.submit` |
| 성공 판정 마커 | `auth.loggedInMarkers` |
| 로그인 화면 진입 버튼 | `auth.loginEntryMarkers` — **여기 없는 버튼은 누르지 않는다** |
| 자격증명 거부 문구 | `auth.errorMarkers` |
| 이메일 | `MOBILE_QA_EMAIL` 환경변수 또는 `.claude/mobile-qa.local.json` |
| 비밀번호 | `MOBILE_QA_PASSWORD` 환경변수 또는 `.claude/mobile-qa.local.json` |

RN 프로젝트에서 흔한 명명은 `email-input` / `password-input` / `login-next-btn`이지만
**추측하지 말고 설정 값을 쓴다.** 자격증명이 없으면 로그인하지 말고 `BLOCKED`을 보고한다.
**비밀번호를 보고서·로그에 평문으로 쓰지 않는다.**

---

## 반드시 먼저 알아야 할 iOS 규칙 3가지

### 규칙 1 — 좌표계: 논리 좌표(points) vs 스크린샷 픽셀

- `mobile_click_on_screen_at_coordinates`, `mobile_list_elements_on_screen`, `mobile_get_screen_size`는
  **논리 좌표(points)** 를 쓴다. (예: iPhone 17 Pro = 402×874)
- `mobile_take_screenshot`, `xcrun simctl io screenshot`은 **픽셀**로 저장한다. (예: 1206×2622, 3배)
- **스크린샷을 보고 요소 위치를 눈대중해서 탭할 때는 픽셀 → 논리 좌표 변환이 필수다.**
  안 하면 화면 밖을 눌러 **앱이 백그라운드로 넘어간다** (그리고 왜 그런지 파악하느라 턴을 태우게 된다):
  ```
  logical_x = pixel_x * (screen_width_pt  / screenshot_pixel_width)    # 예: * (402/1206)
  logical_y = pixel_y * (screen_height_pt / screenshot_pixel_height)   # 예: * (874/2622)
  ```
  `mobile_get_screen_size`로 논리 크기를, 스크린샷 파일 해상도로 픽셀 크기를 구해 비율을 계산한다.
  배율을 3으로 가정하지 마라 — 기기마다 다르다.
- **`mobile_list_elements_on_screen`이 주는 좌표는 이미 논리 좌표다.** 추가 변환이 필요 없다.
  → **가능하면 항상 스크린샷 눈대중이 아니라 요소 목록을 쓴다.** 변환 실수 자체가 사라진다.

### 규칙 2 — top-left → center 변환

`mobile_list_elements_on_screen`이 주는 `(x, y, width, height)`는 **top-left 기준**이다. 탭할 때 center로 변환한다:

```
center_x = x + width / 2
center_y = y + height / 2
```

예: `{"x":189,"y":592,"width":42,"height":23}` → 탭 좌표 `(210, 604)`

BottomSheet/Modal이 열린 상태에서 `mobile_list_elements_on_screen`을 호출하면 에러가 날 수 있다.
그때만 스크린샷 기반 좌표(규칙 1의 변환 적용)로 병행한다.

### 규칙 3 — `mobile_type_keys`는 긴 문자열에서 글자를 누락한다

- **한 번에 2~5글자씩 나눠서 여러 번 호출한다.** 이건 선택이 아니다.
  - 관측 예: 22자 이메일을 `type_keys("qatester1234@example.com")` 한 번에 호출 → 중간 글자 하나가 조용히 빠짐.
    에러가 나지 않으므로 로그인 실패 원인을 엉뚱한 데서 찾게 된다.
  - 올바른 방식: `"qa"` + `"tester"` + `"1234@"` + `"example.com"`
- `submit=true`로 Next/Return을 보낼 수 있지만, **text가 비어 있으면 에러**가 난다.
  (빈 문자열 + submit 조합을 쓰지 마라)
- `\n` 같은 이스케이프는 **리터럴 문자로 입력된다.** 개행 용도로 쓰지 마라.

---

## 절차

### 1단계 — 로그인 화면인지 확인

`mobile_list_elements_on_screen`을 호출해 `auth.testIds.email`이 있는지 본다.

- 없으면 랜딩 화면이다. **`auth.loginEntryMarkers`에 나열된 요소만** 탭해 로그인 화면으로 이동한다.
  ⚠️ 거기 없는 버튼(카카오/Apple 등 외부 OAuth)은 **절대 누르지 마라.** 앱 밖으로 빠져나가
  되돌아오는 데 턴을 크게 낭비한다.
- 그래도 없으면: `mobile_swipe_on_screen`(up) 후 재탐색. **최대 2회.**
  2회 후에도 못 찾으면 스크린샷 1장으로 시각 확인하고, 그래도 없으면 `BLOCKED`을 보고한다.
  같은 탐색을 반복하지 마라.

### 2단계 — 이메일 필드 탭 + 입력 (한 턴에)

1. 요소 목록에서 이메일 필드 좌표를 얻어 **규칙 2**로 center 변환 → `mobile_click_on_screen_at_coordinates`
2. **규칙 3**대로 2~5글자씩 쪼개 `mobile_type_keys` 연속 호출

탭과 입력을 **같은 턴에서** 끝낸다.

### 3단계 — 비밀번호 필드로 이동: **키보드 Next 사용 (필드를 직접 탭하지 마라)**

이것이 iOS에서 가장 많이 실패하는 지점이다.

`secureTextEntry={true}` 필드는 iOS 보안 정책상 **WDA 접근성 트리에 값이 노출되지 않는다.**
항상 placeholder만 보이고, 입력이 됐는지 트리로는 판별할 수 없다.
(단, `pointerEvents="none"` 오버레이를 쓰는 컴포넌트라면 testID로 **좌표 감지 자체는** 가능하다.)

- **절대 금지: 비밀번호 필드를 직접 탭하는 것.**
  Paste/AutoFill 팝업만 뜨고 키보드가 올라오지 않아 입력이 통째로 실패한다.
- **올바른 방법**: 이메일 필드에 입력한 직후, **키보드의 Next 버튼을 탭**해서 포커스를 비밀번호 필드로 넘긴다.
  (`mobile_type_keys`의 `submit=true`로 Next를 보내는 방법도 같은 효과다 — text가 비어 있지 않을 것)

**Paste 팝업이 이미 떠버렸다면**: 화면의 빈 영역을 탭해 닫고(요소가 없는 안전한 지점을
**논리 좌표**로 고를 것), 이메일 필드로 돌아가 Next로 재시도한다.

### 4단계 — 비밀번호 입력: **스크린샷을 찍지 마라**

1. 비밀번호 필드가 포커스된 상태에서 **스크린샷을 찍지 않는다.**
   찍어도 필드는 비어 보이고, 키보드가 안 올라온 것처럼 보인다(실제로는 올라와 있다).
   그 화면을 보고 "입력이 안 됐다"고 오판해 절차를 되돌리는 것이 전형적인 턴 낭비다.
2. 곧바로 **규칙 3**대로 2~5글자씩 쪼개 `mobile_type_keys` 호출.
3. **입력 성공 여부를 여기서 판정하려 하지 마라.** 판정은 6단계에서 화면 전환으로만 한다.

### 5단계 — 제출

- `auth.testIds.submit` 요소를 찾아 center 변환 후 탭.
- 버튼이 키보드에 가려 요소 목록에 없으면: `mobile_type_keys`의 `submit=true`로 키보드의
  Return/Go를 보내거나, `mobile_press_button`으로 ENTER를 시도한다.

### 6단계 — 성공 판정 (유일하게 신뢰할 수 있는 신호)

- 2~4초 기다린 뒤 `mobile_list_elements_on_screen` → `auth.loggedInMarkers` 중 하나가 보이면 **성공**.
- 여전히 로그인 화면이면 실패다. 에러 토스트/배너 텍스트를 요소 목록에서 수집해 보고한다.
- **재시도는 1회까지.** 2단계부터 다시 하되, 실패하면 그 사실을 보고한다.
  같은 절차를 3회 이상 반복하지 마라 — 자격증명이 틀렸거나 백엔드가 문제일 가능성이 높고,
  그건 `BLOCKED`이나 `BUG`로 보고할 사안이지 재시도로 뚫을 사안이 아니다.

---

## 단계별 폴백 요약

| 실패 지점 | 폴백 |
| --- | --- |
| 이메일 필드를 못 찾음 | swipe up 후 재탐색 (최대 2회) → 스크린샷 1장 확인 → `BLOCKED` |
| `list_elements`가 에러 (Modal/BottomSheet) | 스크린샷 + 규칙 1의 픽셀→논리 변환으로 좌표 산출 |
| 탭이 엉뚱한 곳에 들어감 | 규칙 1 변환 누락을 의심. 요소 목록 좌표로 되돌아갈 것 |
| `type_keys`가 글자를 빠뜨림 | 더 잘게 쪼갠다 (2글자 단위). 입력 후 이메일 필드는 트리에서 값 확인 가능 |
| 비밀번호 필드에서 Paste 팝업이 뜸 | 빈 영역 탭으로 닫고 → 이메일 필드 → 키보드 Next로 재진입 |
| 제출 버튼이 키보드에 가림 | `submit=true` 또는 ENTER 키 |
| 로그인 후에도 화면이 그대로 | 에러 텍스트 수집 후 보고. 3회 이상 재시도 금지 |
| dev LogBox 오버레이가 화면을 덮음 | `qa-preflight`의 dismiss 절차 |

---

## 이 절차가 안 맞을 때

앱의 로그인 화면 구조가 위 가정(이메일 → 비밀번호 → 제출)과 다르면
(예: 이메일 먼저 제출 후 비밀번호 화면이 따로 나오는 2단계 로그인, OTP, SSO 전용)
**억지로 맞추지 말고** 관찰한 실제 구조를 `## 학습 (Learned)`에 `CORRECTION`으로 기록하고,
프로젝트의 `.claude/mobile-qa/flows.md`에 로그인 플로우를 문서화하도록 보고서에서 제안한다.
