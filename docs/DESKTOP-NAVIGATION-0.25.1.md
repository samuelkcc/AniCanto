# Desktop navigation: 0.25.1, build 254

Task: Keep the left tools visible and stable while the workspace changes.

## Cause

The navigation column shares the workspace height above the full-width timeline. Eleven tools had a 58-pixel minimum height, large padding, and fixed gaps. The content required 715 pixels. A 1440 by 900 viewport provided 588 pixels. A 1280 by 800 viewport provided 516 pixels. Lower tools were therefore outside the visible column. A render also recreated the column without retaining its scroll position.

## Change

- Retain the tool order and the fixed left edge.
- Use compact labelled buttons in tall windows. Keep the same button positions across Edit and full pages.
- At viewport heights of 920 pixels or less, use icons with translated tooltips and explicit accessible names. At 800 pixels or less, reduce the icon-button spacing further.
- Use a narrow scrollbar when an unusually short workspace still requires scrolling. Preserve its position across renders.
- Keep the timeline across the full window width. No processing, subtitle-source, repair, model, or saved-job rule changes.

## Evidence

Four languages at six viewport sizes pass 24 browser cases. Every tool is visible in these cases. Navigation stays at the left edge below the app bar. Page changes preserve button positions. Four very-short-window cases retain their scroll position after a settings render. All four locales can open Preferences with the keyboard. Original and final screenshots remain in the private validation directory.

The existing 218 focused checks and the front-end model checks pass. These checks use isolated libraries. They do not certify new model inference or whole-film quality. The conversion-worker Python sources remain byte-identical to the installed 0.25.0 sources.

Mac and Windows package checks are recorded with the release. Mac installation waits for the current user conversion to finish and the app to close. Never replace the live bundle while that conversion runs.
