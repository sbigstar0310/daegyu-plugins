# EXAMPLE — screens.md (화면 인벤토리)

> 이것은 **샘플**이다. 실제로는 `$PROJECT_ROOT/.claude/mobile-qa/screens.md`에 프로젝트가 직접 작성한다.
> 아래 내용은 SRR(스르륵) 앱을 예로 든 것이며, 라우트명/testID는
> `shared/constant.ts`의 `ROUTE_NAMES`와 소스의 `testID=`에서 확인한 값이다.
>
> **이 문서의 목적**: 범용 QA 에이전트에게 "이 앱에 어떤 화면이 있고 어떻게 들어가는지"를 알려주어,
> 매번 화면을 탐색하느라 턴을 쓰지 않게 하는 것.

## 작성 형식

각 화면마다: **화면명 · 라우트명 · 진입 경로 · 이 화면임을 식별하는 마커 · 핵심 요소**

---

## 인증 (로그아웃 상태)

### 초기 화면 — `InitialScreen`
- 진입: 앱 콜드스타트 시 미로그인 상태의 첫 화면
- 식별 마커: `kakao-login-btn`, `log-in-link`
- 핵심 요소: `kakao-login-btn`(카카오 로그인), `log-in-link`(이메일 로그인으로), `sign-up-link`(회원가입)
- 비고: Apple 로그인은 iOS 전용

### 이메일 로그인 — `EmailLoginScreen`
- 진입: `InitialScreen` → `log-in-link` 탭
- 식별 마커: `email-input` + `password-input` 동시 존재
- 핵심 요소: `email-input`, `password-input`, `login-next-btn`, `forgot-password-link`
- 비고: `password-input`은 `secureTextEntry` — iOS에서는 값이 접근성 트리에 노출되지 않는다
  (`qa-ios-login`의 SecureTextField 절차 참고)

### 비밀번호 찾기 — `FindPassword1Screen` / `FindPassword2Screen`
- 진입: `EmailLoginScreen` → `forgot-password-link`
- 핵심 요소: `find-pw-email-input`, `find-pw-send-code-btn`, `find-pw-code-input`,
  `find-pw-new-password-input`, `find-pw-confirm-password-input`, `reset-password-btn`

### 회원가입 — `EmailRegisterCheckListScreen` → `EnterEmailScreen` → `EnterCodeScreen` → `EnterNickNameScreen`
- 진입: `InitialScreen` → `sign-up-link`
- 핵심 요소: `checklist-next-btn`, `register-email-input`, `send-code-btn`, `register-code-input`,
  `register-password-input`, `register-confirm-password-input`, `register-next-btn`
- 비고: 실제 이메일 인증 코드가 필요하므로 **자동 QA에 적합하지 않다.** 별도 요청이 없으면 건드리지 않는다.

## 온보딩

### `Onboarding1Screen` ~ `Onboarding5Screen`
- 진입: 신규 가입 직후
- 비고: 기존 테스트 계정은 이미 온보딩을 마쳤으므로 로그인 후 바로 메인탭으로 간다.
  온보딩을 테스트하려면 계정 초기화가 필요하다 — 요청에 명시되지 않았다면 하지 않는다.

## 메인 (로그인 상태)

### 메인탭 — `MainTabs`
- 진입: 로그인 성공 직후
- 식별 마커: **`notification-btn`(권장 — 언어 무관)**. 탭 라벨은 언어에 따라
  ko `별`/`나의 수면`/`마이`, en `Star`/`Sleep`/`My` (출처: `shared/i18n/locales/{ko,en}.json`의 `tabs.*`)
- 탭 구성:
  - **별 / Star** — `StarScreen`
  - **나의 수면 / Sleep** — `MySleepScreen`
  - **마이 / My** — `MyScreen`
- 비고: `MainTabs`는 `AuthProtectedRoute`로 감싸여 있어 **여기 도달했다는 것 자체가 로그인 성공의 증거**다.
  → `auth.loggedInMarkers`로 쓰기에 가장 신뢰도가 높다.

### 별 관련 서브 화면
- `Star10MinBeforeScreen`, `StarOnTimeScreen`, `StarBedEarlyScreen`, `StarRecordScreen`
- 비고: **시간 조건에 의존**하는 화면들이다. 특정 시간대에만 진입 가능할 수 있으므로,
  진입이 안 될 때 앱 버그로 단정하지 말고 시간 조건을 먼저 의심한다.

### 알림 — `NotificationScreen`
- 진입: 메인탭 → `notification-btn`

### 마이 — `MyScreen`
- 핵심 요소: `logout-btn`, `change-password-btn`, `language-link` / `language-select-btn` /
  `language-confirm-btn`(언어 변경), `contact-support-btn`
- **주의**: `logout-btn`을 누르면 세션이 날아가 이후 모든 테스트가 로그인부터 다시 시작된다.
  로그아웃 테스트는 **다른 모든 시나리오를 끝낸 뒤 마지막에** 수행한다.

## 공통 컴포넌트

- 확인 대화상자: `alert-confirm-btn` / `alert-cancel-btn`
- 언어: 한국어(ko) / 영어(en) 지원 — 텍스트 마커로 화면을 식별할 때 **현재 언어 설정에 좌우된다.**
  가능하면 텍스트보다 `testID`를 마커로 쓴다.
