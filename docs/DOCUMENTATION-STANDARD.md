# Documentation standard: all record files use ASD-STE100 style

Effective 2026-10-28, set by Samuel. This file is the single authority for the documentation language rule.
Rule sources: the bullet in `AGENTS.md`, and rule 7 in the Working Agreement of `docs/CODEX-HANDOVER.md`.

## 1. Rule

Every record file in this project is written in English. It follows the ASD-STE100 Simplified Technical English style. This applies to the whole project, not only to the desktop line or the iPad line, and not only to the handover log.

A record file is a file that describes work, decisions, status, findings, or evidence. The following are record files:

- `docs/CODEX-HANDOVER.md`, and every new entry added to it.
- Every `docs/*.md` workflow, spec, audit, review, plan, checklist, register, guide, and acceptance note.
- `docs/IPAD-FOLLOWUP-REGISTER.md`, and any register created later.
- `docs/README.md`, and any index or map file created later.
- `docs/RECOVERY-WORKFLOW-CONTRACT.json`, and any other contract or machine-readable record under `docs/`.
- `docs/archive/` files, when a thread edits them.
- Validation receipts that carry prose, for example `mobile/Validation/*.json`.
- Source and resource code comments, and help text written for operators.

A new record file starts in English. Do not create a new record file in Chinese or Japanese.

## 2. Files outside this rule

These files keep their required languages. They are product content or legal content, not records of work:

- Privacy policies: `docs/IPAD-PRIVACY-POLICY.md` plus the `.zh-HK`, `.zh-CN`, and `.ja` copies.
- Legal and licence text: `docs/LICENSING.md` and the copies under `docs/en/`, `docs/ja/`, `docs/zh-CN/`, `docs/zh-HK/`.
- Store listing and demo copy: `docs/en/DEMO.md`, `docs/ja/DEMO.md`, `docs/zh-CN/DEMO.md`, `docs/zh-HK/DEMO.md`.
- App UI strings and locale files, and the in-app Help centre source `studio/web/help.js`.

If a record file must name user-facing wording, it quotes the exact string, then explains it in English.

### Product language

The `zh-HK` interface and Help text use written Traditional Chinese (Hong Kong).
Do not use spoken Cantonese grammar in control labels, notices, or help paragraphs.
Generated Cantonese translations and character dialogue retain spoken Hong Kong grammar.
Source dialogue, subtitles, test fixtures, and quoted speech keep their original wording.
Responses to Samuel in this chat remain Cantonese.

## 3. Style rules

1. Write short sentences. Keep each sentence at 20 words or fewer where you can.
2. Write one idea in one sentence.
3. Use active voice. Name the actor: "Codex rebuilt the host," not "the host was rebuilt."
4. Use one term for one thing, and use it in every file. Do not alternate between "job", "task", and "run" for the same object.
5. Use plain, common words. Do not use idioms, jokes, irony, or rhetorical questions.
6. Use the present tense for current status, and the past tense for finished work.
7. State order explicitly. Use "First", "Then", "Next", or numbered steps.
8. Separate fact from judgement. Write "Not verified" for anything you did not test, and name the test that would verify it.
9. Keep mode names, revision stamps, settings labels, and build numbers exactly as the code spells them.
10. Do not use vague quantifiers such as "some", "several", or "a few". Write the count.

## 4. Material you must not translate

Copy these exactly as they appear:

- File paths, folder names, bundle IDs, UDIDs, revision stamps, version numbers, build numbers, SHAs, test names, commands, and log lines.
- Real speech used as evidence or as a test fixture, for example `出現喺`, `出而家`, `いい`, `ええ`, `おい`, `救命`, `啊`, `ああ`.
- Numbers, timings, and budget values.

If you translate any of the above, the test or the evidence stops working.

## 5. Header line

Add this line under the H1 of every record file you create or convert:

```
> Language standard: English, ASD-STE100 style. See docs/DOCUMENTATION-STANDARD.md.
```

If part of that file is still Chinese or Japanese, name the pending parts on the next line. Never leave the pending scope silent.

## 6. Migration of old files

1. Entries and files written before 2026-10-28 keep their original language until a planned pass converts them. Change the language only. Do not change their meaning.
2. When you edit a record file, convert the lines you touch in the same pass.
3. Convert long files in date-range batches. One batch must fit in one thread window.
4. Record each pass as a new entry in `docs/CODEX-HANDOVER.md`. State which files and which date ranges you converted, and what is still pending.
5. Do not renumber, reorder, or rewrite history. Do not delete a Chinese block before its English replacement is in place. Check the boundary lines after every large replace.

## 7. Check

```sh
rg -l '[\p{Han}\p{Hiragana}\p{Katakana}]' docs            # record files that still contain CJK
rg -c '[\p{Han}\p{Hiragana}\p{Katakana}]' docs/<file>     # lines with CJK in one file
```

The check finds candidates, not violations. Lines that hold quoted fixtures from section 4 are correct. Read each hit before you change it.

## 8. Current state at 2026-10-28

- Converted to English: `docs/CODEX-HANDOVER.md` (header, Working Agreement, Handover Protocol, General Rules, Work Line Map, 2026-10-22 snapshot, and the three newest entries), `docs/DESKTOP-IPAD-RECOVERY-WORKFLOW.md` (full file), `docs/DESKTOP-RECOVERY-PENDING.md` (full file), `docs/DESKTOP-WORKFLOW.md` (full file), `docs/README.md` (index lines), `docs/IPAD-FOLLOWUP-REGISTER.md` (header, banner, three newest entries).
- Contract JSON: `docs/RECOVERY-WORKFLOW-CONTRACT.json` has no CJK lines.
- Still to convert: 74 record files under `docs/` still contain CJK lines. The largest block is the older entries in `docs/CODEX-HANDOVER.md` (1881 lines), then `docs/IPAD-DESKTOP-WORKFLOW-PARITY.md` (97), `docs/IPAD-VLCKIT-RELEASE-REVIEW.md` (92), `docs/IPAD-GPT-V4-LICENSE-REVIEW.md` (61), and `docs/IPAD-FOLLOWUP-REGISTER.md` (53). Convert them in date-range batches, one batch per thread window.
