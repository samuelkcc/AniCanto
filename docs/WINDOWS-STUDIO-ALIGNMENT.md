> Historical implementation notes. The current common Tauri interface and
> acceptance limits are documented in [SHARED-ARCHITECTURE.md](SHARED-ARCHITECTURE.md).

# Windows studio alignment — 0.23.0 (build 141)

Mac baseline: installed 0.22.12, build 140. This release changes the Windows
studio and shared desktop metadata; it does not replace the installed Mac app.

The previous Windows desktop was a separate compact Qt implementation. Sharing
`Resources/worker.py` did not make its interface equivalent to SwiftUI. This
release rebuilds its main arrangement using the Mac workspace as the reference.
`Resources/studio-interface.json` records the page order, dimensions, engine order,
inspector sections, default categories and theme colours used by Windows.
The Mac source remains SwiftUI; it does not render from this JSON.

## Layout and operation

- Welcome: full contained themed cover, language selection, two mode selection
  cards, one Enter action, setup disclosure, plan and package management,
  overlaid information drawer with no second cover.
- Basic: video shelf on the left, preview / milestone journey / current-line
  audition / output in the middle, shared production choices on the right.
- Expert: one right-aligned action group, independently toggleable navigation,
  project browser and inspector; preview above an editable bilingual transcript;
  full-width timeline underneath all three upper columns.
- Inspector: Production, Dialogue, Picture and Mix. Dialogue separates existing
  takes, new takes and timing / voice adjustments. Available takes determine
  audition/adoption availability, and inference controls use backend limits.
- Roles: album and reference details, staged per-cue matching, observed portraits,
  image import / current-frame crop, role creation / merge and undoable assignments.
- Review: searchable recording history by failure/review/repair state, audition
  rejected audio, accept a complete recording or open its line for editing.
- Produce: voice/subtitle/sample operations, caption settings, clip controls,
  regeneration/reanalysis and separate versioned submissions.
- Queue, Terminal, production defaults, model centre, preferences and project /
  export management are embedded workspace pages. Defaults have six categories;
  model management separates voice/text/speech/audio/runtime packages.
- Both modes use the same Store and editor document. A submitted request remains
  immutable; changing future defaults cannot rewrite a paused request.

Native widgets, GPU adapters and available model formats differ by platform.
This is not a claim of pixel-identical rendering or completed native Windows /
CUDA acceptance. Advanced Mac editing interactions must be assessed on Windows
as part of that acceptance; matching the main arrangement alone does not prove
all Mac behaviour or inference quality.

## “Needs attention” reporting defect

One verified defect was in the Windows result projection: shared batch conversion
can emit a per-episode error, later emit an ordinary batch summary and exit zero.
The old projection replaced the visible message with that summary. It could leave
only “Needs attention”, without its actual cause. This does **not** identify the
underlying failure in the user's deleted executable or that specific conversion.

Each new attempt now writes its own attempt receipt and process log. Fatal events
are retained independently from later progress. Stderr and final stdout fragments
are drained before completion. Known Windows DLL/instruction/native crashes have
specific diagnostics. Existing exports cannot make a failed new attempt look
successful; successful auditions/subtitle/sample operations need no movie.
Pausing is distinct from failing; old attempt evidence survives retries.

Missing source files produce an actionable persistent banner. Missing runtime or
verified tool files trigger setup repair before production, with one bounded
verification retry. Starting during an unfinished deployment schedules production
after verification; starting with no verified setup begins deployment automatically.
It no longer just opens a plan and leaves the video idle. This does not pretend that arbitrary inference failures are
always recoverable. The shared conversion repair policy remains responsible for
per-line recovery.

## Verification

Evidence directory: `.build/qa292/`.

- Full Python regression suite: 820 tests passed. Final desktop interactions and setup/cleanup controls
  were also checked separately against the release candidate.
- `tests/windows_desktop_qa.py`: real six-second Unicode-named media, both modes,
  10 pages, immutable requests, real streamed UTF-8 events, 2,000 in-memory
  playhead callbacks, rapid seeking, English guide and MIT information.
- `tests/windows_studio_parity_qa.py`: both interface languages, every page,
  1280-pixel width, bilingual edits, undo/redo, role assignment, timing edits,
  manual dialogue, clip splits, source subtitle evidence, mix settings and
  backend parameter limits. A real child process emits an error followed by
  an exit-zero summary; the banner, stderr log and restart evidence are checked.
- PE/payload verification checks Windows x64 GUI format, the embedded ZIP and
  every manifest hash, and compares packaged Python modules with current source.

No Windows PC or NVIDIA GPU was connected for this build. Native first-run
installation, Windows multimedia rendering, actual GPU synthesis and a complete
Windows episode export still require on-device acceptance. No user models,
projects or recordings were deleted by these tests.
