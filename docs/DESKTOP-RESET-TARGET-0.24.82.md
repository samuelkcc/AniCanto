# Desktop reset target and queue order · 0.24.82

Reset state opens a separate confirmation naming the video selected when the restart menu was opened. Background selection changes do not change that target. Preparing the plan and committing the reset show an inline status. Failures remain visible; a stale confirmation requires a fresh plan. Cancelling preparation ignores late responses. Committing disables duplicate submission and closing until the operation returns.

Successful reset closes the menu and selects the confirmed video. Source media, old recordings, exports and installed models remain on disk; the previous reset archive policy is unchanged. Reset does not start conversion.

Start all follows the displayed pending-video order, including paused and review items when applicable. Selecting a video is an inspection action and does not move it to the front. An explicit single-video restart continues to target that video. Start is blocked while a reset confirmation is pending. Active processing must be paused before resetting.

## Cause and validation

The previous UI silently returned when the menu target differed from the current selection. Separately, batch Start promoted the selected paused/review item over the visible queue order. An isolated real-UI test reproduced both together: waiting B first, paused A selected, reset B produced no confirmation, batch Start launched A. This demonstrates a matching code path, not a production event trace proving what changed the selection on the user machine.

Regression cases cover pinned selection, visible order, RPC failures, busy states, stale confirmation, cancellation, duplicate prevention and explicit single-video restart. No TTS model, sampling preset or conversion repair policy changed.
