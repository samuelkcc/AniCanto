# Shared user guide maintenance

Language standard: English, ASD-STE100 style. See `docs/DOCUMENTATION-STANDARD.md`.

Task: Keep user instructions consistent with the installed workflow on each platform.

## Sources

- `docs/APPLICATION-USER-GUIDE.json` is the single source for operation chapters and platform-specific navigation.
- `docs/WORKFLOW-CONTROLS-GUIDE.json` is the single source for workflow-control definitions. Resolve its item IDs through `controlRefs`. Do not copy and alter these definitions in an operation chapter.
- `docs/DESKTOP-IPAD-RECOVERY-WORKFLOW.md` and its JSON contract define the workflow and acceptance limits. A manual is not evidence that a platform implements a feature.

## Format

The application guide has schemaVersion1, a revision, four locales and chapters. A chapter has an ID, aliases, platforms, localized title and summary, and sections. A section has an ID, platforms, localized title, localized body paragraphs, controlRefs and steps. Platforms are desktop, ipad and iphone. Apply both chapter and section filters. Resolve each control ID from the control guide. Render titles and body in the chosen locale. Preserve chapter IDs or provide aliases when reorganizing.

## Change procedure

1. Read the operation chapter, referenced controls and current platform mapping before each user-visible change.
2. Check the actual settings, frozen request, permissions and current navigation. Keep source clocks, display clocks and delivered audio distinct.
3. Update the canonical chapter in all four locales in the same task. Use platform scope for a real difference. Do not create a second platform definition of a shared rule.
4. Assign one writer for shared content. Other owners provide narrow source paragraphs and consume the completed source.
5. Copy the exact canonical JSON and exact control guide into each package. Record revision and SHA-256. Do not claim another platform is installed from a copied file.
6. Verify links, search, language fallback, platform filtering and actual rendered instructions. Record focused tests and remaining native or whole-film acceptance.
7. Record source, tested, packaged and installed states separately in the shared handover. Resume never changes an old frozen policy or returns spent attempts.

## Desktop consumption

`scripts/prepare_shared_studio.py` copies both canonical files byte for byte and creates JS exports with hashes. `studio/web/help.js` filters the operation chapters for desktop and resolves current control definitions. It does not use a second historical chapter array.

## Boundaries

Desktop has no mobile Reading, Learning or purchase workflow. Mobile does not advertise desktop Drama3, CUDA or desktop filesystem controls. Native mobile owners maintain their loader and navigation. Do not publish private mobile source with the desktop source export.
