---
name: progress
description: Report the live status of long-running jobs (training/eval runs, tmux sessions, background processes, GPU work) in a concise, ETA-first summary. Use whenever the user asks "진행상황 / status / how's it going / where are we / 어디까지 됐어" or wants a snapshot of what's running. Project-agnostic — discovers jobs from tmux, logs, and processes rather than assuming any fixed layout.
---

# progress — live job status, ETA first

Goal: answer "what's running and when will it finish?" in a compact snapshot the
user can read in 5 seconds. **ETA is the headline, not an afterthought** — every
running job gets a real-timing finish estimate, never "it's running."

Do NOT block the turn waiting for jobs. Gather current state, report, done. If the
user wants to be pinged on completion, arm a `Monitor` (see step 4) — don't sleep.

## 1. Discover what's running (don't assume a layout)

Run these in parallel; skip whatever returns nothing. Adapt to the project — a repo
may use only some of these.

- **tmux sessions** (the usual home of long runs):
  `tmux ls 2>/dev/null` — note session names; runs often tee to a log.
- **Log files, freshest first** (find the active ones by mtime):
  `ls -lt logs/*.log 2>/dev/null | head` (also try `*.log`, `run*/`, `outputs/`,
  `nohup.out`). The most-recently-modified log is almost always the live job.
- **Background processes**: `ps aux | grep -E "python|train|eval|torchrun" | grep -v grep`
- **GPU work** (if ML): `nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total --format=csv,noheader`
  and `nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory --format=csv,noheader`.
- **This session's own background tasks / monitors**: recall any `Monitor`,
  `run_in_background`, or Workflow you started this session — include them.

If nothing is found, say so plainly ("돌아가는 잡 없음") and stop — don't invent status.

## 2. Read progress + compute a REAL ETA

For each active log, pull the last progress line and turn it into a finish time.

- **tqdm bars** are the common case: `12/33 [04:40<36:43, 183.64s/it]`. The bracket
  already gives `[elapsed<remaining, rate]` — **use its `remaining` directly**; don't
  recompute from scratch. Grab the last one: `grep -oE "[0-9]+/[0-9]+ \[[^]]*\]" LOG | tail -1`.
- **Beware nested bars**: an inner per-step/per-block bar (`7/8`) is NOT overall
  progress — find the OUTER loop bar (batches/epochs). If you see `21/33` and `7/8`,
  the `21/33` is the real progress. Report the outer; mention inner only if useful.
- **Custom logs** (step counters, epoch markers, `elapsed_steps=`): find current vs
  total, get rate from timestamps if present, extrapolate. State the assumption.
- **Give a clock time, not just a duration**: "~36분 남음 (≈16:55 완료)" beats "~36분".
  Compute finish = now + remaining.
- **ALWAYS report clock times in KST (Asia/Seoul), the user's timezone.** Servers here
  run **UTC** — reporting raw `date` output is off by +9h and misleads the user. Read the
  wall clock as `TZ='Asia/Seoul' date '+%H:%M'` and derive every "now" and ETA from that.
  When an ETA crosses midnight, mark the date (e.g. "≈01:10 KST (다음날)").
- If a job's own tail shows it already emitted a done-marker (e.g. `CELL_DONE`,
  `EXIT`, `GRID_QUEUE_DONE`, exit code), report it as finished, not running.

## 3. Health check — don't report a dead job as "running"

A log that hasn't grown is a stall, not progress. Cross-check:

- Is the log's mtime recent (seconds/minutes ago), or stale (hasn't moved)? A stale
  log on a job that should be active = likely crashed/hung → flag it.
- Scan the tail for REAL failures, but **do not false-positive on generated content**:
  in code/eval runs, model output often contains `raise ValueError`, `Error`,
  `except` — those are data, not crashes. Match real tracebacks only:
  `grep -E "Traceback \(most recent|CUDA out of memory|OutOfMemory|^Killed|Killed$|Segmentation fault"`.
  When unsure whether a match is a crash or echoed output, open the tail and look
  before declaring failure.
- Note pipeline waits: a job parked in a `WAIT` state (waiting on an upstream job's
  done-marker) is healthy-but-blocked, not stuck — say what it's waiting for.

## 4. Report format — compact, ETA-first, honest

Use ASCII code blocks for any aligned columns (the user's markdown tables don't
render for them). Keep it scannable. Structure:

- One line per job group: `name  progress  → ETA (clock time)`.
- Group related jobs (e.g. a 3-GPU split) under a heading.
- Call out anything abnormal (stall, crash, blocked-waiting) explicitly and first.
- If jobs form a pipeline, end with a 2–3 line **timeline** of what unlocks when.
- If any run is long, proactively offer a cheaper/faster variant (fewer problems,
  smaller batch, single GPU) — but only offer, don't change anything.

Example shape:
```
프로브 배치-민감도 (b8 2셀 남음)
  marker_b8   21/33 @183s/it  → ~36분 (≈16:55)
  d1_b8       19/33 @136s/it  → ~31분 (≈16:50)
MATH 3-GPU
  GPU2 qA(ep2)  MATH block 3/8 실행 중
  GPU3 qB(ep6)  WAIT — 프로브 d1_b8 대기
```

## 5. Boundaries

- **Read-only by default.** This skill inspects and reports. Do not kill, launch,
  or modify jobs unless the user explicitly asks in the same breath.
- Don't propose next experiments or design changes — just report state (unless asked).
- Match the user's language. Keep it short: they asked "how's it going," not for an essay.
