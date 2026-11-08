# Desktop dubbing update 0.25.51 / build 425

Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.

Task: Update dubbing languages from retained original source without repeating source analysis.

A changed language starts a new translation from the original source text.
A same-language update can retain its verified script. Previous outputs remain unchanged.
Add another audio track retains previous tracks. Replace one audio track changes only the selected target in the new output.
Unknown source lines retain original audio and a review issue. They do not stop other valid lines.
Target retries receive the previous actual draft. Attempts remain bounded and persist on resume.
Verified source allocations, clocks, separation and voice-reference caches are reused.
The first-draft Cantonese examples include emotional crying and distinguish calls for help.
Mac now includes the exact contextual example tables selected by its worker.
Optional AI checks, first audible takes and overlap permissions remain unchanged.

Package and publication evidence is recorded separately. Windows native GPU execution and whole-film listening require device acceptance.
