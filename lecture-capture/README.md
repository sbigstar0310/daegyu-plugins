# lecture-capture

macOS에서 듣고 있는 Zoom 강의를 녹음하고, Zoom 창만 녹화하고, 실시간으로 한국어를 받아쓴 뒤 강의 노트로 정리합니다.

- **오디오:** Core Audio tap([AudioTee](https://github.com/makeusabrew/audiotee))을 씁니다. 에어팟으로 들으면서 그대로 녹음되고, BlackHole은 필요 없습니다.
- **영상:** ScreenCaptureKit으로 Zoom 회의 창만 캡처하고, raw 프레임을 ffmpeg에 넘겨 5분 단위 mkv(10fps)로 저장합니다. 다른 창이 겹쳐도 찍히지 않습니다.
- **전사:** mlx-whisper(`whisper-large-v3-turbo`)로 5분 구간마다 로컬에서 받아씁니다. 외부로 업로드하지 않습니다.
- **점검:** `watch.sh`를 Claude Code의 Monitor에 걸어서 구간마다 상태를 보고합니다.

## 사용

Claude Code에서 "줌 강의 녹음해서 정리해줘"라고 하면 스킬이 아래 순서로 진행합니다. 직접 실행할 때:

```bash
scripts/setup.sh                      # 최초 1회: 빌드 + 설치
scripts/start.sh ~/Desktop/lecture_x  # 녹음·녹화·전사 시작 (exit 3 = 무음)
scripts/peek.sh  ~/Desktop/lecture_x  # 진행 중 구간 바로 받아쓰기
scripts/watch.sh ~/Desktop/lecture_x  # 상태 점검 스트림
scripts/stop.sh  ~/Desktop/lecture_x  # 종료 + 오디오/전사/영상 병합
```

요구 사항: Apple Silicon, macOS 14.2 이상, ffmpeg, Xcode CLT(swift), uv.
권한: 시스템 설정 → 화면 및 시스템 오디오 녹음 → 터미널 앱을 켜야 합니다. 권한이 없으면 무음으로 녹음됩니다.

강의를 녹음·녹화하기 전에 주최 측 허락을 확인하세요.
