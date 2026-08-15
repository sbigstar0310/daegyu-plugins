---
name: qa-preflight
description: React Native / Expo 앱의 GUI QA를 시작하기 전에 테스트 가능한 상태(Metro 실행, 시뮬레이터/에뮬레이터 부팅, 앱 설치·실행, 로그인 여부 판별)를 확보한다. iOS 시뮬레이터나 Android 에뮬레이터에서 앱을 테스트·조작하기 직전에 사용한다.
when_to_use: 모바일 QA 세션 시작 시, "앱이 안 뜬다"·"디바이스가 없다"·"로그인부터 해야 하나?" 상황, 또는 테스트 도중 앱이 죽어 상태를 복구해야 할 때.
---

# QA Preflight — 테스트 가능한 상태 만들기

목표는 하나다: **에이전트 턴을 최소로 쓰고 "앱이 떠 있고, 어느 화면인지 알고 있는" 상태에 도달하는 것.**

이 스킬은 **의도와 판단 기준**을 정의한다. 기계적인 절차는 번들 스크립트 `srr-qa-preflight`에 있다.
스크립트를 먼저 쓰고, 실패했을 때만 아래 수동 절차로 내려온다.

---

## 0. 설정 로드 (모든 것의 전제)

앱별 사실은 **절대 추측하지 않는다.** 아래 순서로 해결한다:

1. 환경변수 (`MOBILE_QA_*`)
2. `$CLAUDE_PROJECT_DIR/.claude/mobile-qa.local.json` — **비밀값 전용**, gitignore 대상
3. `$CLAUDE_PROJECT_DIR/.claude/mobile-qa.config.json` — 커밋되는 비민감 설정
4. 내장 기본값 — **범용적으로 참인 값에만** 적용 (Metro 포트 `8081`)

```bash
cat "$CLAUDE_PROJECT_DIR/.claude/mobile-qa.config.json"
```

읽는 키:

| 키 | 용도 |
| --- | --- |
| `metro.port` | Metro 번들러 포트 (기본 8081) |
| `ios.bundleId` / `ios.simulatorUdid` / `ios.simulatorName` / `ios.installCommand` | iOS 대상 |
| `android.package` / `android.serial` / `android.installCommand` | Android 대상 |
| `auth.strategy` | 로그인 방식 (예: `email-password`) |
| `auth.testIds.{email,password,submit}` | 로그인 필드 식별자 |
| `auth.loggedInMarkers` / `auth.loggedOutMarkers` | 로그인 여부 판정 마커 |
| `auth.loginEntryMarkers` | 랜딩 화면에서 **로그인 화면으로 들어가기 위해 눌러도 되는 요소**. 아래 주의 참고 |
| `auth.errorMarkers` | 자격증명 거부 시 나타나는 인라인 에러 문구 |
| `quirks.androidImePackage` | 입력기 패키지 (Gboard 복구용) |
| `quirks.dismissLogBox` | dev LogBox 오버레이 자동 dismiss 여부 |

> **`loginEntryMarkers` 주의**: 랜딩 화면에 자격증명 필드가 아예 없고 먼저 "로그인" 링크를 눌러야
> 하는 앱이 많다. 이때 **여기 나열되지 않은 버튼은 절대 누르지 마라.** 카카오/Apple 같은 외부
> OAuth 버튼을 잘못 누르면 앱 밖 웹뷰로 빠져나가 복구에 턴을 크게 낭비한다.

**설정 파일이 없으면 여기서 멈추고 `BLOCKED`을 보고한다.** 앱 소스를 뒤져 bundle ID를 추론하지 마라 —
빌드 variant/flavor마다 다르고, 틀린 ID로 launch하면 조용히 아무 일도 일어나지 않아 디버깅에 턴을 낭비한다.

**자격증명**은 설정 파일에 없다. `MOBILE_QA_EMAIL` / `MOBILE_QA_PASSWORD` 환경변수 또는
`mobile-qa.local.json`에서만 온다. 로그인이 필요한데 없으면 그것도 `BLOCKED`이다.

---

## 1. 빠른 경로: 번들 스크립트

```bash
srr-qa-preflight all 2>/dev/null          # stdout만 남겨 파싱 (stderr는 사람용 진행 로그)
srr-qa-preflight ios --start-metro        # Metro가 꺼져 있으면 백그라운드로 띄우기
```

인자는 `ios` | `android` | `all` (기본 `all`). 주요 옵션:

- `--start-metro` — **이 플래그가 없으면 Metro가 꺼져 있는 것은 하드 실패다.** (의도된 설계:
  예고 없는 백그라운드 프로세스보다 명확한 에러가 낫다) Metro를 띄워도 되는 상황이면 이 플래그를 준다.
- `--udid` / `--serial` — 설정 대신 특정 디바이스 지정
- `--no-launch`, `--no-connect`(dev-client 딥링크 생략), `--no-open-sim`
- `--boot-timeout N`(기본 120), `--timeout N`(기본 30)

**출력**: stdout에 `=== SRR-QA-PREFLIGHT-SUMMARY ===` … `=== END-SUMMARY ===` 블록만 나온다.
모든 키는 항상 존재하며 값이 비어 있을 수 있다. 읽을 키:

```
PREFLIGHT_RESULT=OK|DEGRADED|BLOCKED
METRO=UP|DOWN|PORT_BUSY_NOT_METRO|STARTED
IOS_STATUS=READY|BLOCKED|UNAVAILABLE|NOT_REQUESTED
IOS_LOGIN_STATE=LOGGED_IN|LOGGED_OUT|APP_NOT_RUNNING|UNKNOWN
IOS_DEEPLINK_OPENED=0|1
IOS_FIX=<BLOCKED일 때 사람이 실행할 명령>
ANDROID_STATUS= / ANDROID_LOGIN_STATE= / ANDROID_DEEPLINK_OPENED= / ANDROID_FIX=   (동일 형식)
```

**종료 코드**: `0` OK · `1` DEGRADED(일부 플랫폼만 준비됨) · `2` 사용법 오류 · `3` BLOCKED · `4` 설정 오류

**해석 원칙**:

- `IOS_STATUS=READY` / `ANDROID_STATUS=READY`면 준비된 것이다. 디바이스 부팅·앱 실행 여부를
  MCP 도구로 **다시 확인하지 마라** — 순수한 턴 낭비다.
- `*_STATUS=BLOCKED`이면 `*_FIX`에 사람이 실행할 명령이 들어 있다. **그대로 보고서에 인용한다.**
  에이전트가 우회를 시도하지 않는다.
- `*_DEEPLINK_OPENED=0`이면 앱이 아직 **Expo 개발 서버 선택 메뉴**에 머물러 있을 수 있다.
  이 상태에서 요소 목록을 뜨면 앱 화면이 아니라 런처 메뉴가 나온다 — 앱 버그로 오해하지 마라.
- 종료 코드 `1`(DEGRADED)은 요청한 두 플랫폼 중 하나만 준비된 경우다. 준비된 쪽 테스트는 진행하고,
  안 된 쪽은 `BLOCKED`으로 보고한다.

`command not found`면 스크립트가 없는 것이다. **실패가 아니다.** 아래 수동 절차로 내려간다.

---

## 2. 수동 폴백 — 공통: Metro

dev client 빌드는 Metro 없이는 흰 화면이나 "Could not connect to development server"로 멈춘다.

```bash
PORT=8081   # 설정의 metro.port
curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/status"
```

- 200이면 실행 중.
- 아니면 프로젝트 루트에서 백그라운드로 띄운다 (포그라운드로 띄우면 세션이 블록된다):
  ```bash
  npx expo start --port 8081
  ```
  실행 후 준비될 때까지 `/status`를 폴링한다. 무작정 긴 `sleep`을 넣지 않는다.
- 릴리즈/프로덕션 빌드를 테스트 중이면 Metro는 필요 없다. 설정이나 요청에서 판단한다.

---

## 3. 수동 폴백 — iOS

```bash
xcrun simctl list devices booted                    # 부팅된 것이 있는가
xcrun simctl boot "$UDID"                           # 없으면 설정의 ios.simulatorUdid로 부팅
open -a Simulator                                   # GUI 표시 (스크린샷에 필요)
xcrun simctl get_app_container booted "$BUNDLE_ID" app   # 설치 여부: 성공하면 설치됨
xcrun simctl launch booted "$BUNDLE_ID"
```

- 부팅은 즉시 끝나지 않는다. `xcrun simctl bootstatus "$UDID" -b`로 기다린다.
- `get_app_container`가 실패하면 **앱 미설치**다. 설정의 `ios.installCommand`
  (예: `npx expo run:ios --device <UDID>`)로 설치한다. 이건 수 분이 걸리므로
  **호출자에게 먼저 알리고**, 턴 예산이 부족하면 `BLOCKED`으로 보고하는 편이 낫다.
- launch 후 접근성 트리가 채워지기까지 시간이 걸린다. **2초로 부족한 경우가 있다** — 요소 목록이
  비어 있으면 스크린샷을 찍기 전에 한 번 더 기다린 뒤 `mobile_list_elements_on_screen`을 재호출한다.

> **iOS는 셸로 탭할 수 없다.** `idb`가 설치되어 있어도 신뢰하지 마라 — 이 절차가 개발된 머신에서는
> Python 3.14 비호환으로 `idb --version`조차 traceback으로 죽었다.
> iOS의 모든 인터랙션은 **Mobile MCP 도구**로 한다. `xcrun simctl`은 관리·관찰 전용이다.

---

## 4. 수동 폴백 — Android

```bash
adb devices                                          # device 상태인 항목이 있는가
adb -s "$SERIAL" shell pm list packages | grep "$PACKAGE"       # 설치 여부
adb -s "$SERIAL" shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1
```

- 디바이스가 없으면: `emulator -list-avds` → `emulator -avd <AVD> &` → `adb wait-for-device`.
- `unauthorized` 상태면 실기기 화면의 USB 디버깅 승인 대화상자를 사람이 눌러야 한다 → `BLOCKED`.
- 디바이스가 여러 대면 **반드시 `-s <serial>`을 붙인다.** 안 붙이면 `adb`가 에러로 끝난다.
- 미설치면 설정의 `android.installCommand`로 설치. iOS와 같은 시간 경고가 적용된다.

### 에뮬레이터 저장공간

에뮬레이터 디스크가 차면 설치가 조용히 실패한다. 의심되면:

```bash
adb shell pm trim-caches 999999999
```

---

## 5. 로그인 여부 판별 — **가장 큰 턴 절약**

대부분의 RN 앱은 인증 세션을 디스크에 유지한다(Firebase Auth, SecureStore, AsyncStorage 등).
따라서 **앱을 재실행해도 이미 로그인된 상태인 경우가 많고, 로그인 절차는 대개 불필요하다.**
로그인부터 시도하는 습관은 매 세션 5~10턴을 그냥 버린다.

```bash
srr-qa-state android 2>/dev/null    # 인자는 ios 또는 android 하나만 (all 불가)
```

**출력** (stdout은 `KEY=value` 줄만):

```
STATE=LOGGED_IN|LOGGED_OUT|APP_NOT_RUNNING|UNKNOWN
PLATFORM=ios|android
REASON=<MARKER_MATCH | AMBIGUOUS_MARKERS | NO_MARKERS_MATCHED | PROCESS_NOT_FOUND |
        IOS_SHELL_DETECTION_LIMIT | NO_DEVICE | DUMP_FAILED | TIMEOUT | ...>
EVIDENCE=<판정 근거가 된 attr=value>     # 알 수 있을 때
SCREENSHOT=<경로>                        # iOS에서 캡처했을 때
```

**종료 코드**: `0` LOGGED_IN · `10` LOGGED_OUT · `11` APP_NOT_RUNNING · `12` UNKNOWN ·
`2` 사용법 · `3` 환경 불가 · `4` 설정 오류

### ⚠️ iOS는 설계상 판정하지 않는다

셸만으로 iOS 뷰 계층을 읽을 신뢰할 방법이 없다(이 머신에서 `idb`가 고장나 있다).
그래서 이 스크립트는 **앱이 실행 중인 iOS에 대해서는 항상 `STATE=UNKNOWN`
(`REASON=IOS_SHELL_DETECTION_LIMIT`)을 반환하고 스크린샷만 남긴다.** 추측하지 않는 것이 의도된 동작이다.

→ **iOS의 로그인 여부는 에이전트가 `mobile_list_elements_on_screen`으로 직접 판정해야 한다.**
`UNKNOWN`을 "로그아웃"으로 해석해 곧장 로그인 절차에 들어가지 마라 — 이미 로그인된 상태에서
로그인 화면을 찾느라 턴을 태우는 전형적인 실패다.
(`APP_NOT_RUNNING`은 iOS에서도 정확하게 판정된다.)

### 수동 판별

1. `mobile_list_elements_on_screen`으로 화면 요소를 가져온다 (스크린샷보다 싸고 정확하다).
2. 설정의 마커와 대조:
   - `auth.loggedOutMarkers` 중 하나라도 보이면 → **로그아웃 상태**, 로그인 필요
   - `auth.loggedInMarkers` 중 하나라도 보이면 → **로그인 상태**, 로그인 절차 **전체를 건너뛴다**
   - 둘 다 없으면 → 스플래시/로딩 중일 수 있다. 한 번 더 기다린 뒤 재확인. 그래도 모호하면
     스크린샷 1장으로 확인하고, 그 결과를 `## 학습 (Learned)`에 `FACT`로 남긴다.
3. Android 수동 대안:
   ```bash
   adb shell uiautomator dump /sdcard/ui.xml && adb shell cat /sdcard/ui.xml
   ```
   `resource-id` / `content-desc` / `text`에서 마커를 찾는다.
   화면 전환 애니메이션 중에는 dump가 실패할 수 있다 → 잠깐 기다린 뒤 재시도.

**로그인이 필요하다고 판정된 경우에만** 플랫폼별 로그인 스킬로 넘어간다
(`qa-ios-login` / `qa-android-login`).

---

## 6. 화면을 가리는 방해물 치우기

### dev client LogBox 빨간 오버레이 (양 플랫폼)

- dev 빌드에서 `console.error`가 발생하면 빨간 오버레이가 화면 전체를 덮는다.
  **이것은 대체로 앱 버그가 아니라 dev 로깅이다** — 즉시 FAIL로 판정하지 마라.
- 대응: 화면 하단의 **"Dismiss"** 를 탭한다. 실패하면 앱 terminate → relaunch → 다시 dismiss.
- 단, **오버레이에 표시된 에러 텍스트는 보고서에 기록한다.** 실제 결함의 신호일 수 있다.
- 설정의 `quirks.dismissLogBox`가 `false`면 자동으로 닫지 말고 그대로 보고한다.

### Android 소프트 키보드 (IME) 상태 오염

- Gboard가 **플로팅 모드**로 저장되어 있으면 풀 키보드가 뜨지 않아 입력이 통째로 실패한다.
  화면에 키보드가 보이지 않는데 필드가 포커스된 것처럼 보이면 이 상태를 의심한다.
- 복구: 설정의 `quirks.androidImePackage`(보통 `com.google.android.inputmethod.latin`) 데이터 초기화
  ```bash
  adb shell pm clear com.google.android.inputmethod.latin
  ```
- 에뮬레이터 AVD `config.ini`에 `hw.keyboard=no`를 설정하고 재시작하면 재발을 막을 수 있다.
- 한글 등 비-ASCII 입력이 필요한데 해당 키보드가 미설치인 경우가 있다.
  ASCII만 필요하면 `adb shell input text`로 우회할 수 있다.

---

## 7. 완료 판정

아래를 모두 만족하면 프리플라이트 완료다. 보고서 첫머리에 이 요약을 한 줄로 남긴다:

```
preflight: metro=ok device=booted app=running logged_in=yes|no|unknown
```

자동으로 해결할 수 없는 항목이 있으면 **테스트를 억지로 진행하지 말고** `BLOCKED`으로 보고한다.
사람이 해야 하는 일(USB 디버깅 승인, 긴 네이티브 빌드, 없는 자격증명)을 에이전트가 턴을 태워
우회하려 드는 것이 가장 흔한 실패 모드다.
