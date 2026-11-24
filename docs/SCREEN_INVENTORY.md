# ORALSENSE — SCREEN INVENTORY (PROPOSED)

Status: screens 1–22 are implemented. Screens 1–16 are the clinical/research assessment workflow. Screens 17–22 add the protocol library, study directory and details, trial-level analysis, and advisory AI quality review. Screens 23–27 (longitudinal comparison, analytics, export, settings, and the remaining recovery states) are not built. This inventory remains the map, not a claim that screens 23–27 exist.

This is the complete proposed screen inventory, not a requirement to build 27 unrelated routes. Some screens are separate pages; others are focused states within the same page. Build it as one cohesive app with shared layouts and reusable components. The active assessment experience, data integrity, and results visualization receive the most effort.

27 screens across 8 sections.

**Dual-workflow structure:** [DUAL_WORKFLOW_CONTEXT.md](DUAL_WORKFLOW_CONTEXT.md) resolves the dual-workflow screen plan. One platform, two workflows (Clinical and Research), a shared assessment engine, and the same 27 screens. No extra screen is mandatory. Clinical visits are not forced into the research-study model. Every assessment links to the correct person, context, protocol, and session history. On dual-workflow structure, `DUAL_WORKFLOW_CONTEXT.md` wins over this inventory. Scientific and safety rules in `PRODUCT_CONTEXT.md` still win over everything. This inventory is retained.

---

## 1. Entry & workspace — 3 screens

Public-facing pages and access to the research application.

| # | Screen | Purpose |
|---|---|---|
| 1 | Landing page | Explain OralSense, its purpose, and key features. |
| 2 | Sign in | Access the research workspace. |
| 3 | Workspace / account setup | Set up the research workspace and basic preferences. |

## 2. Dashboard — 1 screen

| # | Screen | Purpose |
|---|---|---|
| 4 | Research dashboard | Overview of participants, recent assessments, studies, and items needing review. |

## 3. Participant management — 4 screens

| # | Screen | Purpose |
|---|---|---|
| 5 | Participant directory | Search, filter, and browse participant records. |
| 6 | Add participant | Create a pseudonymous participant record and enter necessary study information. |
| 7 | Participant profile | View participant details, study memberships, and assessment history. |
| 8 | Participant assessment history | Inspect previous sessions and compare compatible results over time. |

## 4. Assessment & testing — 8 screens

This is the core of OralSense. Give this section the most design and development attention.

| # | Screen | Purpose |
|---|---|---|
| 9 | Assessment selection | Choose a new assessment or resume an existing session. |
| 10 | Assessment configuration | Select participant, study, sensory modality, and protocol version. |
| 11 | Readiness & protocol instructions | Review procedure, required materials, relevant safety checks, and session prerequisites. |
| 12 | Active testing | Display the current trial, instructions, response controls, and progress. The clinician administers the physical stimulus. |
| 13 | Adaptive trial progression | Show the next trial selected by the configured assessment method and explain the next required action. |
| 14 | Pause / resume session | Recover a saved session, inspect progress, and continue without losing recorded trials. |
| 15 | Session review | Inspect recorded responses, missing entries, invalid or skipped trials, and corrections before finalization. |
| 16 | Assessment results | Present calculated outcomes, supporting plots, uncertainty where justified, and data-quality indicators. |

Active testing (12) and adaptive progression (13) can share one route and layout. Each state must be designed properly; each does not need its own URL.

## 5. Protocols & studies — 4 screens

| # | Screen | Purpose |
|---|---|---|
| 17 | Protocol library | Browse available assessment protocols. |
| 18 | Protocol details | Inspect procedure, response types, parameters, and requirements. |
| 19 | Protocol configuration & versioning | Create or configure a protocol and preserve its versions. |
| 20 | Study directory & study details | Create studies and manage their participants, protocols, and assessments. |

## 6. Analysis & AI quality review — 3 screens

| # | Screen | Purpose |
|---|---|---|
| 21 | Trial-level analysis | Inspect response patterns and the data behind calculated results. |
| 22 | AI quality review | Review advisory flags, explanations, and confidence labels from the AI service. |
| 23 | Longitudinal comparison | Compare compatible assessments for a participant across sessions. |

AI review must remain separate from the actual measurements. It flags patterns for human review; it never diagnoses participants or silently modifies results.

## 7. Research data & exports — 2 screens

| # | Screen | Purpose |
|---|---|---|
| 24 | Research analytics | Summarize study-level data, completion, and available outcome distributions. |
| 25 | Data & exports | Filter eligible records and export trial-level and assessment data. |

## 8. Settings, recovery & system states — 2 screens

| # | Screen | Purpose |
|---|---|---|
| 26 | Workspace settings | Configure account, workspace, and application preferences. |
| 27 | System / recovery states | Handle failed saves, interrupted sessions, unavailable AI review, empty results, and recoverable errors. |

Screen 27 is a collection of designed states rather than one ordinary page. A research application must make it obvious when data is saved, incomplete, or unavailable.

---

## Navigation

```text
Overview
  Dashboard
Participants
  Directory · Add participant · Profile · History
Assessments
  Selection · Configuration · Readiness · Testing · Pause/resume · Review · Results
Protocols
  Library · Details · Configuration · Versions
Studies & Research
  Study directory · Study details · Analytics
Analysis
  Trial analysis · AI review · Longitudinal comparison
Data & Exports
  Filter · Preview · Export
Settings
  Workspace preferences · Recovery and system states
```

---

## Proposed build phases

**Phase 1 — Core product:** dashboard, participant directory, add participant, participant profile, assessment configuration, readiness, active testing, session review, results.

**Phase 2 — Scientific functionality:** protocol library and versioning, trial-level analysis, adaptive progression, reliable pause/resume, AI quality review.

**Phase 3 — Research management:** study management, longitudinal comparisons, analytics, exports, settings, and the remaining account screens.

**Phase 4 — Final polish:** animations, transitions, responsive behavior, accessibility, loading states, and error recovery.

The owner's note that this structure "follows common research-platform patterns (central study dashboards, participant records, protocol-guided data capture, data review, and export workflows)" came with a citation that was not preserved. Treat it as **unverified** until a source is recorded.

---

## Open questions vs. existing context (owner decision pending)

These points in the proposal conflict with rules already in `docs/PRODUCT_CONTEXT.md`, `docs/ENGINEERING_CONTEXT.md`, and `docs/OPENAI_INTEGRATION.md`. They are recorded here, not resolved.

1. **Adaptive progression is in Phase 2.** The product context makes the adaptive engine the core differentiator, and says a product that is only forms, database, and charts is the wrong product. Phase 1 as written would end as exactly that. Option: move adaptive progression (13) and the threshold/uncertainty analysis behind results (16) into Phase 1.
2. **(Resolved by `MASTER_PROMPT.md` §7 and §19: UI/UX, accessibility, loading, and error states are built with each screen, not left to the end.)** **Accessibility, loading states, and error recovery are in Phase 4.** The engineering context treats accessibility as part of correctness, requires real loading, saving, saved, and error states for every async operation, and forbids losing collected trials. Option: build those states with each screen, and keep only animations, transitions, and responsive polish for Phase 4. Pause/resume (14) is data-loss protection, so it would arguably belong in Phase 1 as well.
3. **No screen owns the combined oral-sensory profile.** The product context requires a multidimensional profile (tactile, thermal, chemesthetic) computed from real results. Results (16) is per assessment. Option: add the profile to participant profile (7), or make it a state of results (16).
4. **Readiness "safety checks" (11).** Instructions, materials, and safety checks must come from the published protocol a procedure is based on. OralSense must not invent stimulus magnitudes or safety procedures.
5. **Analytics "outcome distributions" (24).** Show observed distributions only. No normal bands, reference ranges, or cutoffs.
6. **Landing page (1).** Hackathon constraints say not to start with landing pages. It is not in Phase 1 in this proposal, which is consistent; it should stay late.
