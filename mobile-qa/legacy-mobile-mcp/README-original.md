# mobile-qa — React Native / Expo GUI QA 플러그인

iOS 시뮬레이터와 Android 에뮬레이터에서 RN/Expo 앱을 조작해 테스트하고 보고서를 반환하는
Claude Code 서브에이전트 2종 + 검증된 절차 스킬 3종 + 셸 스크립트 번들.

**플러그인 자체는 어떤 앱에도 종속되지 않는다.** 앱별 사실은 전부 프로젝트 설정에서 읽는다.

> 디렉토리명이 `plugins/srr-qa/`인 것은 이관 과정의 잔재다. 플러그인의 실제 이름은
> 매니페스트의 `name` 필드인 **`mobile-qa`** 이고, 스킬/에이전트 네임스페이스도 그것을 따른다
> (`/mobile-qa:qa-preflight`, `@mobile-qa:mobile-qa-ios`). 디렉토리는 나중에 `plugins/mobile-qa/`로 정리한다.

---

## 4개 레이어 모델

이 플러그인이 동작하려면 4가지가 필요하고, **각각이 사는 곳이 다르다.** 이 구분이 설계의 핵심이다.

| # | 레이어 | 사는 곳 | 담는 것 | 누가 쓰는가 | 커밋? |
| --- | --- | --- | --- | --- | --- |
| 1 | **플러그인 (범용)** | `plugins/srr-qa/` | 에이전트 역할, 절차 골격, **도구 gotcha**, 보고 계약 | 플러그인 저자 | ✅ |
| 2 | **설정 (앱별 사실)** | `$PROJECT_ROOT/.claude/mobile-qa.config.json` | bundleId, package, UDID, testID, 마커, Metro 포트 | 프로젝트 | ✅ |
| 2b | **비밀값** | `$PROJECT_ROOT/.claude/mobile-qa.local.json` 또는 환경변수 | 테스트 계정 이메일/비밀번호 | 프로젝트 | ❌ **gitignore** |
| 3 | **앱 스펙 (앱별 의도)** | `$PROJECT_ROOT/.claude/mobile-qa/` | `screens.md`, `flows.md` — 화면 인벤토리, 정상 플로우, 합격 기준 | 프로젝트 | ✅ |
| 4 | **에이전트 메모리 (학습)** | `.claude/agent-memory/<agent-name>/MEMORY.md` | 세션을 거치며 누적된 실전 지식 | 에이전트/메모리 관리자 | ✅ |

경계 판단 기준 한 줄:

- **다른 RN 앱에서도 참인가?** → 레이어 1 (플러그인)
- **이 앱의 사실인가?** → 레이어 2
- **이 앱이 무엇을 해야 하는가?** → 레이어 3
- **써 보고 알게 된 것인가?** → 레이어 4

레이어 3이 특히 중요하다. 범용 에이전트는 앱이 뭘 해야 하는지 모른다.
`flows.md`가 없으면 에이전트는 요청받은 시나리오만 수행하고 **합격 기준을 스스로 지어내지 않는다.**

---

## 구성 요소

```
plugins/srr-qa/
├── .claude-plugin/plugin.json    # name: mobile-qa
├── agents/
│   ├── mobile-qa-ios.md          # iOS QA 서브에이전트
│   └── mobile-qa-android.md      # Android QA 서브에이전트
├── skills/
│   ├── qa-preflight/SKILL.md     # 테스트 가능 상태 확보 + 로그인 여부 판별
│   ├── qa-ios-login/SKILL.md     # iOS 결정적 로그인 (SecureTextField 대응)
│   └── qa-android-login/SKILL.md # Android 로그인 (스크립트 우선)
├── bin/                          # PATH에 자동 등록되는 실행 스크립트
│   ├── srr-qa-preflight
│   ├── srr-qa-android-login
│   └── srr-qa-state
├── examples/                     # 복사해서 쓰는 샘플 (그대로 쓰지 말 것)
│   ├── mobile-qa.config.json
│   ├── mobile-qa.local.json
│   ├── screens.md
│   └── flows.md
└── README.md
```

### 에이전트

| 에이전트 | 프리로드 스킬 | 조작 방식 |
| --- | --- | --- |
| `mobile-qa-ios` | `qa-preflight`, `qa-ios-login` | **Mobile MCP 전용** (iOS는 셸 탭 불가) |
| `mobile-qa-android` | `qa-preflight`, `qa-android-login` | **ADB 우선**, MCP는 화면 분석용 |

둘 다 `disallowedTools: Write, Edit` — **코드를 수정할 수 없다.** 발견한 것은 보고서로만 전달한다.

### 왜 스킬을 `skills:` 프론트매터로 프리로드하는가

에이전트가 "메모리 파일을 읽어라"라는 지시를 **기억해서 실행**하는 데 의존하면,
잊거나 건너뛰는 순간 절차 지식 없이 탐색을 시작한다.
`skills:` 필드는 스킬 **전문을 시작 시점에 컨텍스트로 주입**하므로 그 실패 모드가 사라지고,
Read에 쓰던 턴도 없어진다.

`tools:`에는 `Skill`도 함께 넣었다. 프리로드와는 별개로, 프리로드되지 않은 스킬을
실행 중에 추가 호출할 수 있게 하기 위해서다.

---

## 설치 / 활성화

### 개발 중 (설치 없이 로드)

```bash
claude --plugin-dir ./plugins/srr-qa
```

변경 후에는 재시작 없이 `/reload-plugins`로 반영한다.

### 확인

- 에이전트: `/context`의 Custom Agents에 `mobile-qa:mobile-qa-ios`, `mobile-qa:mobile-qa-android`
- 스킬: `/help` → Custom commands에 `/mobile-qa:qa-preflight` 등
- 스크립트: Bash에서 `srr-qa-preflight --help`가 bare command로 실행되는지
- 실패하면 `/plugin`의 **Errors** 탭 확인

### 검증

```bash
claude plugin validate ./plugins/srr-qa
```

---

## 프로젝트 쪽 준비 (앱마다 1회)

```bash
mkdir -p .claude/mobile-qa
cp plugins/srr-qa/examples/mobile-qa.config.json .claude/mobile-qa.config.json
cp plugins/srr-qa/examples/screens.md            .claude/mobile-qa/screens.md
cp plugins/srr-qa/examples/flows.md              .claude/mobile-qa/flows.md
```

그리고 값을 **이 프로젝트에 맞게 고친다.** 샘플 값을 그대로 두면 안 된다.

자격증명은 둘 중 하나로만 준다:

```bash
export MOBILE_QA_EMAIL='qa@example.com'
export MOBILE_QA_PASSWORD='...'
```

또는 `.claude/mobile-qa.local.json`에 넣고 **반드시 gitignore**한다:

```
.claude/mobile-qa.local.json
```

### 설정 해결 순서

1. 환경변수 (`MOBILE_QA_*`)
2. `.claude/mobile-qa.local.json` — 비밀값 전용
3. `.claude/mobile-qa.config.json` — 커밋되는 비민감 설정
4. 내장 기본값 — **범용적으로 참인 값에만** (Metro 포트 `8081`)

### 설정 키

| 키 | 설명 |
| --- | --- |
| `metro.port` | Metro 포트 (기본 8081) |
| `ios.bundleId` | iOS 번들 ID |
| `ios.simulatorUdid` / `ios.simulatorName` | 대상 시뮬레이터 |
| `ios.installCommand` | 미설치 시 설치 명령 |
| `android.package` | Android 패키지명 |
| `android.serial` | 디바이스 serial (여러 대일 때 필수) |
| `android.installCommand` | 미설치 시 설치 명령 |
| `auth.strategy` | 로그인 방식 (예: `email-password`) |
| `auth.testIds.{email,password,submit}` | 로그인 필드 식별자 |
| `auth.loggedInMarkers` | 로그인 상태에서만 보이는 testID/텍스트 |
| `auth.loggedOutMarkers` | 로그아웃 상태에서만 보이는 testID/텍스트 |
| `auth.loginEntryMarkers` | 랜딩 화면에서 로그인 화면으로 들어가기 위해 **눌러도 되는** 요소 |
| `auth.errorMarkers` | 자격증명 거부 시 나타나는 인라인 에러 문구 |
| `quirks.androidImePackage` | 입력기 패키지 (Gboard 복구용) |
| `quirks.dismissLogBox` | dev LogBox 오버레이 자동 dismiss 여부 |

`auth.loginEntryMarkers`는 **안전장치**다. 랜딩 화면에 자격증명 필드가 없어 먼저 "로그인" 링크를
눌러야 하는 앱에서, 스크립트와 에이전트는 **여기 나열되지 않은 버튼을 누르지 않는다.**
카카오/Apple 같은 외부 OAuth 버튼을 실수로 눌러 앱 밖으로 빠져나가는 것을 막는다.

환경변수: `MOBILE_QA_CONFIG`, `MOBILE_QA_IOS_BUNDLE_ID`, `MOBILE_QA_IOS_UDID`,
`MOBILE_QA_IOS_DEVICE_NAME`, `MOBILE_QA_ANDROID_PACKAGE`, `MOBILE_QA_ANDROID_SERIAL`,
`MOBILE_QA_METRO_PORT`, `MOBILE_QA_EMAIL`, `MOBILE_QA_PASSWORD`

`auth.loggedInMarkers`는 **인증 가드 뒤에만 존재하는 요소**로 고르는 것이 가장 신뢰도가 높다.
텍스트보다 `testID`를 선호한다 — 다국어 앱에서 텍스트 마커는 언어 설정에 따라 깨진다.

---

## 사용

QA는 **iOS와 Android를 항상 병렬로** 돌린다. 한쪽만 돌리지 않는다.

권장 `max_turns`: 단순 확인 15 / 멀티스텝 인터랙션 20 / 복합 E2E 30.

사전 조건: Metro 실행 중, 시뮬레이터 부팅됨, `adb devices`에 디바이스 있음.
(`srr-qa-preflight all`이 대부분 알아서 해준다)

---

## 보고서 계약

에이전트는 **반드시 마지막 메시지에서 텍스트 보고서를 반환**한다. 서브에이전트의 결과는
그 텍스트가 전부이므로, 보고서를 못 내면 세션 전체가 유실된다.

보고서에 반드시 들어가는 것:

1. 테스트별 `PASS` / `FAIL` / `BLOCKED`, 재현 단계, 증거(스크린샷 경로·로그)
2. `턴 예산: 사용 N / 배정 M · 최다 소모 단계: <단계명> (K턴)` 한 줄
3. `## 학습 (Learned)` 블록 — **기계 판독 가능 형식**

```
TYPE | claim | evidence | confidence
```

- `TYPE` ∈ `FACT` | `CORRECTION` | `GOTCHA` | `WORKAROUND` | `UNRESOLVED`
- `evidence` **필수** — 근거를 못 대는 항목은 적지 않는다
- `confidence` ∈ `high` | `medium` | `low`
- 배울 게 없으면 **블록을 생략하지 않고** `none` 한 줄
- **PASS/FAIL 판정 기준을 바꾸자는 제안은 여기 적지 않는다** (본문 `비고`로)
- 앱 버그는 여기가 아니라 `### BUG:` 항목으로

이 블록이 레이어 4(에이전트 메모리)와 레이어 1/2/3으로 지식이 흘러 들어가는 **유일한 통로**다.
에이전트 자신은 Write/Edit이 없어 파일을 못 고치므로, 여기에 적히지 않은 발견은 영구히 사라진다.

---

## 플러그인에 넣지 말아야 할 것

이 플러그인의 가치는 **범용성**에 있다. 아래를 플러그인 파일에 넣는 순간 다른 프로젝트에서 못 쓰게 된다.

- ❌ bundle ID / package name / 시뮬레이터 UDID / 디바이스명
- ❌ 실제 testID 문자열, 화면 이름, 네비게이션 구조
- ❌ 테스트 계정 이메일·비밀번호 (**어떤 경우에도 비밀번호는 플러그인 파일에 쓰지 않는다**)
- ❌ 특정 앱의 합격 기준

반대로 아래는 플러그인에 있어야 한다 — 어느 RN 앱에서나 참이기 때문이다.

- ✅ `mobile_type_keys`가 긴 문자열에서 글자를 누락함 → 2~5글자 분할
- ✅ iOS `secureTextEntry` 필드가 WDA 접근성 트리에 노출되지 않음
- ✅ iOS 논리 좌표(points) vs 스크린샷 픽셀 변환
- ✅ Android 고밀도 기기에서 MCP 좌표 탭이 어긋남 → `adb shell input tap`
- ✅ dev client LogBox 오버레이 대응
- ✅ Gboard 플로팅 모드 오염 → 입력기 `pm clear`
- ✅ 요소 확인은 스크린샷보다 `mobile_list_elements_on_screen`
