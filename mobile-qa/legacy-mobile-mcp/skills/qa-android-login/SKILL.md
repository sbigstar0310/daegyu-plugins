---
name: qa-android-login
description: Android 에뮬레이터/실기기에서 React Native / Expo 앱의 이메일+비밀번호 로그인을 수행한다. 스크립트(srr-qa-android-login)로 턴 소모 없이 처리하는 것이 기본이고, 실패 시 adb shell input 기반 수동 절차로 폴백한다. ADB 네이티브 좌표 탭 규칙, mobile_type_keys 글자 누락 회피, Gboard 상태 오염 복구를 포함한다.
when_to_use: Android에서 앱에 로그인해야 할 때, 탭이 엉뚱한 곳에 들어갈 때, 키보드가 안 뜨거나 입력이 안 먹힐 때, mobile_type_keys가 글자를 빠뜨릴 때.
---

# Android 로그인 — 스크립트 우선, 수동은 폴백

**Android는 셸에서 화면을 완전히 구동할 수 있다.** 따라서 로그인은 원칙적으로
**에이전트 턴을 0으로 쓰고** 스크립트 한 번으로 끝난다. 손으로 탭하기 시작하는 순간 이미 지고 있는 것이다.

**전제**: `qa-preflight`로 앱이 실행 중이고 **로그인이 필요하다고 판정된 상태**여야 한다.
이미 로그인되어 있으면 이 스킬 전체를 건너뛴다.

---

## 입력값 (전부 설정에서, 추측 금지)

| 값 | 출처 |
| --- | --- |
| 패키지명 | `android.package` |
| 디바이스 serial | `android.serial` (여러 대일 때 필수) |
| 이메일 / 비밀번호 / 제출 버튼 testID | `auth.testIds.{email,password,submit}` |
| 성공 판정 마커 | `auth.loggedInMarkers` |
| 로그인 화면 진입 버튼 | `auth.loginEntryMarkers` — **여기 없는 버튼은 누르지 않는다** |
| 자격증명 거부 문구 | `auth.errorMarkers` |
| 입력기 패키지 | `quirks.androidImePackage` |
| 이메일 | `MOBILE_QA_EMAIL` 환경변수 또는 `.claude/mobile-qa.local.json` |
| 비밀번호 | `MOBILE_QA_PASSWORD` 환경변수 또는 `.claude/mobile-qa.local.json` |

RN 프로젝트에서 흔한 명명은 `email-input` / `password-input` / `login-next-btn`이지만
**추측하지 말고 설정 값을 쓴다.** 자격증명이 없으면 로그인하지 말고 `BLOCKED`을 보고한다.

> **testID가 Android에서 어디로 가는가**: React Native의 `testID`는 Android 뷰의
> **`resource-id`** 로 노출된다(일부 컴포넌트는 `content-desc`). 그래서 uiautomator dump에서
> 이름으로 찾을 수 있고, **좌표를 하드코딩할 필요가 없다.** 하드코딩된 좌표는 화면 크기가 바뀌면 전부 깨진다.

---

## 1. 빠른 경로: 스크립트

```bash
srr-qa-android-login
```

- 자격증명은 `MOBILE_QA_EMAIL` / `MOBILE_QA_PASSWORD` 또는 `mobile-qa.local.json`에서 **스스로 읽는다.**
  명령줄로 비밀번호를 넘기지 마라 — 프로세스 목록과 셸 히스토리에 남는다.
- 요소는 `uiautomator dump`로 `resource-id`/`content-desc` 기준 탐색한다. **좌표 하드코딩 없음.**
- **이미 로그인된 세션을 감지하면 즉시 `0`으로 조기 종료**한다. 그냥 항상 먼저 돌려도 안전하다.

**종료 코드 → 대응**:

| 코드 | 의미 | 에이전트가 할 일 |
| --- | --- | --- |
| `0` | 로그인 완료 (또는 이미 로그인 상태) | **바로 테스트로.** MCP로 재확인하지 마라 |
| `1` | 사용법/설정 오류, 필수 키 누락 | `BLOCKED` 보고 — 설정을 고쳐야 한다 |
| `2` | 사용 가능한 adb 디바이스 없음/모호 | `BLOCKED` — 에뮬레이터 기동 또는 `serial` 지정 |
| `3` | 패키지 미설치 | `BLOCKED` — 설치 명령 안내 |
| `4` | 앱이 안 뜨거나 UI가 알려진 상태에 도달 못함 | 수동 폴백 시도 |
| `5` | 로그인 화면/자격증명 필드를 못 찾음 | 수동 폴백 (2절). `loginEntryMarkers` 설정 확인 |
| `6` | 입력이 신뢰성 있게 안 됨 (readback 불일치) | 규칙 3(IME) 확인 후 수동 폴백 |
| `7` | **앱이 자격증명을 거부** (`auth.errorMarkers` 감지) | **재시도 금지.** 계정/백엔드 문제로 보고 |
| `8` | 제출은 됐으나 로그인 후 UI가 안 나타남 | 네트워크/백엔드 의심. 1회만 재시도 |
| `9` | adb / uiautomator 인프라 실패 | 디바이스 상태 확인 후 수동 폴백 |

`7`(거부)과 `8`(타임아웃)의 구분이 중요하다. **`7`은 절대 재시도하지 마라** — 비밀번호가 틀린 것이고,
반복 시도는 계정 잠금을 유발할 수 있다.

`command not found`면 스크립트가 없는 것이다. **실패가 아니다.** 아래 수동 절차로 내려간다.

---

## 반드시 먼저 알아야 할 Android 규칙 3가지

### 규칙 1 — 탭은 `mobile_click_on_screen_at_coordinates`가 아니라 `adb shell input tap`

- MCP의 좌표 탭은 고밀도(high-dpi) 디바이스에서 **스케일이 어긋나 엉뚱한 곳을 누른다.**
  - 관측 예: Pixel 7 Pro 560dpi — MCP 스크린샷 660×1432 vs 네이티브 1440×3120 (약 2.18배).
- **올바른 방법**:
  1. `mobile_list_elements_on_screen`으로 요소의 **접근성 트리 좌표(네이티브 픽셀)** 확인
  2. `adb shell input tap <x> <y>`로 네이티브 좌표를 직접 탭
- 좌표는 top-left 기준이므로 center 변환: `center_x = x + w/2`, `center_y = y + h/2`
- BottomSheet/Modal이 열린 상태에서는 `list_elements` 호출이 실패할 수 있다 → uiautomator dump 병행.

### 규칙 2 — `mobile_type_keys`는 긴 문자열에서 글자를 누락한다

- **2~5글자씩 나눠 여러 번 호출한다.** (관측 예: `"sbigstar"` 한 번 → 글자 누락. `"sb"` + `"igstar"`로 분할)
- **더 나은 대안: `adb shell input text "..."`.** 셸 입력은 이 누락 문제가 없고 한 번에 들어간다.
  - 특수문자는 셸과 `input`이 각각 해석하므로 인용에 주의한다.
  - **공백은 `%s`로 인코딩**해야 한다. `input text`는 공백을 인자 구분자로 본다.
  - **비밀번호는 명령줄에 평문으로 노출된다.** 가능하면 환경변수를 셸 안에서 확장하고,
    그 명령줄을 **보고서에 그대로 붙여넣지 않는다.**

### 규칙 3 — 소프트 키보드(IME) 상태가 오염될 수 있다

- Gboard가 **플로팅 모드**로 저장되어 있으면 풀 키보드가 뜨지 않아 입력이 통째로 실패한다.
  필드는 포커스된 것 같은데 키보드가 안 보이면 이 상태를 의심한다.
- 복구:
  ```bash
  adb shell pm clear com.google.android.inputmethod.latin   # 설정의 quirks.androidImePackage
  ```
  (앱 데이터가 아니라 **키보드 앱** 데이터를 지우는 것이다 — 로그인 세션에는 영향이 없다)
- AVD `config.ini`에 `hw.keyboard=no`를 두고 재시작하면 재발을 막을 수 있다.
- 한글 등 비-ASCII 키보드가 기본 미설치인 에뮬레이터가 있다. ASCII만 필요하면
  `adb shell input text`로 IME를 우회할 수 있다.

---

## 2. 수동 폴백 절차

디바이스가 여러 대면 아래 모든 `adb`에 `-s "$SERIAL"`을 붙인다.

### 2-1. 요소 트리 덤프

```bash
adb shell uiautomator dump /sdcard/ui.xml && adb shell cat /sdcard/ui.xml
```

- 화면 전환 애니메이션 중에는 dump가 실패한다("could not get idle state" 류) → 잠깐 기다린 뒤 재시도.
- 여기서 `resource-id`에 설정의 testID가 들어간 노드의 `bounds="[x1,y1][x2,y2]"`를 읽는다.
  탭 좌표는 그 중심: `((x1+x2)/2, (y1+y2)/2)`.
- MCP 쪽을 쓰고 싶으면 `mobile_list_elements_on_screen`도 동일한 네이티브 좌표를 준다.

### 2-2. 로그인 화면인지 확인

- 이메일 필드가 없으면 랜딩 화면이다. **`auth.loginEntryMarkers`에 나열된 요소만** 탭해서 로그인 화면으로 간다.
  - ⚠️ **거기 없는 버튼은 절대 누르지 마라.** 카카오/Apple 같은 외부 OAuth 버튼을 누르면
    앱 밖 웹뷰/브라우저로 빠져나가고, 되돌아오는 데 턴을 크게 낭비한다.
  - `loginEntryMarkers`가 비어 있는데 자격증명 필드도 없으면 → 설정 부족이다. `BLOCKED` 보고.
- 그래도 없으면 swipe up 후 재탐색 **최대 2회** → 그래도 없으면 `BLOCKED` 보고. 반복 탐색 금지.

### 2-3. 이메일 입력

```bash
adb shell input tap <email_cx> <email_cy>
adb shell input text "$MOBILE_QA_EMAIL"
```

- MCP `type_keys`를 쓸 경우에만 2~5글자 분할 규칙(규칙 2)을 적용한다.
- 입력 후 dump를 다시 떠서 필드의 `text` 속성으로 **실제로 들어갔는지 확인할 수 있다.**
  (iOS와 달리 Android는 일반 필드 값이 트리에 노출된다 — 이 확인은 싸고 확실하다.)

### 2-4. 비밀번호 입력

```bash
adb shell input tap <pw_cx> <pw_cy>
adb shell input text "$MOBILE_QA_PASSWORD"
```

- Android는 iOS와 달리 **비밀번호 필드를 직접 탭해도 된다.** (iOS의 SecureTextField 제약은 Android에 없다)
- 다만 비밀번호 필드의 `text`는 마스킹되어 보이므로 **값 자체를 검증하려 하지 마라.**
  판정은 2-6에서 화면 전환으로만 한다.
- 키보드가 안 뜨면 규칙 3(IME 복구)을 적용하고 이 단계부터 재시도한다.

### 2-5. 제출

```bash
adb shell input tap <submit_cx> <submit_cy>
```

- 버튼이 키보드에 가려 트리에 없으면 먼저 키보드를 내린다:
  ```bash
  adb shell input keyevent 111    # KEYCODE_ESCAPE — 키보드 닫기
  ```
  그 뒤 dump를 다시 떠서 좌표를 얻는다. 또는 `adb shell input keyevent 66`(ENTER)으로 제출한다.

### 2-6. 성공 판정

- 2~4초 기다린 뒤 dump 또는 `mobile_list_elements_on_screen` → `auth.loggedInMarkers`가 보이면 **성공**.
- `auth.errorMarkers` 중 하나가 보이면 **자격증명 거부**다. 재시도하지 말고 그대로 보고한다.
- 여전히 로그인 화면이고 에러 문구도 없으면 제출이 안 갔거나 응답 대기 중이다.
  에러 토스트/배너 텍스트를 수집하고,
  필요하면 logcat을 붙인다:
  ```bash
  adb logcat -d --pid=$(adb shell pidof <PACKAGE>) | tail -50
  ```
- **재시도는 1회까지.** 3회 이상 반복하지 마라 — 자격증명이 틀렸거나 백엔드 문제일 가능성이 높고,
  그건 `BLOCKED`이나 `BUG`로 보고할 사안이다.

---

## 단계별 폴백 요약

| 실패 지점 | 폴백 |
| --- | --- |
| 스크립트 `command not found` | 수동 절차(2절)로 진행. 실패로 취급하지 않음 |
| 스크립트 비-0 종료 | stderr 이유를 보고서에 남기고 수동 절차로 진행 |
| `uiautomator dump` 실패 | 잠깐 대기 후 재시도 → 그래도 실패하면 `mobile_list_elements_on_screen` |
| 탭이 엉뚱한 곳에 들어감 | 규칙 1 위반 의심. `mobile_click_on_screen_at_coordinates` 쓰지 말 것 |
| 키보드가 안 뜸 / 입력 무반응 | 규칙 3 — IME `pm clear` 후 재시도 |
| `type_keys` 글자 누락 | `adb shell input text`로 전환 |
| 공백/특수문자가 깨져 들어감 | 공백은 `%s`로 인코딩, 인용 재확인 |
| 제출 버튼이 키보드에 가림 | keyevent 111로 키보드 닫기 → 재dump, 또는 keyevent 66 |
| 로그인 후에도 화면이 그대로 | 에러 텍스트 + logcat 수집 후 보고. 3회 이상 재시도 금지 |

---

## 위험한 명령 (실수 주의)

- `adb shell pm clear <APP_PACKAGE>` — **앱 데이터 전체 삭제**. 로그인 세션과 온보딩 상태까지 날아간다.
  "깨끗한 상태에서 시작"이 테스트 요구사항일 때만 쓰고, **쓰기 전에 보고서에 명시한다.**
  (IME 복구용 `pm clear`는 **키보드 패키지** 대상이므로 이것과 다르다 — 헷갈리지 마라.)

---

## 이 절차가 안 맞을 때

로그인 화면 구조가 위 가정(이메일 → 비밀번호 → 제출)과 다르면 억지로 맞추지 말고,
관찰한 실제 구조를 `## 학습 (Learned)`에 `CORRECTION`으로 기록하고
프로젝트의 `.claude/mobile-qa/flows.md`에 문서화하도록 보고서에서 제안한다.
