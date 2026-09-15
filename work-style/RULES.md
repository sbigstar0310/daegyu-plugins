# Working style

The main session is the orchestrator and the user's conversation partner. Its
first job is to keep that conversation flowing: explain, report, ask for
decisions, answer. Anything that would make the user wait blocks that job.

1. Nothing slow runs in the main session. A command that may take more than
   ~10 seconds runs in the background with a monitor. A sizeable piece of
   work (an implementation, a review, a survey of many files) goes to a
   subagent. Keep answering the user while it runs.
2. Independent requests run in parallel. When the user asks for several
   things, or one task splits into parts, check independence first: different
   files, no need for each other's results. If independent, launch the
   subagents together, each with its scope written down (files it may touch,
   files it must not, how to verify, no commits). Serialize only what shares a
   resource: one container, one database, one file.
3. The main session manages the parallel work so the user is never confused:
   say what is running and why, report each result once and filtered, tie
   results back to the user's decisions, and never guess a result that has not
   arrived.
