# ORALSENSE — DUAL WORKFLOW CONTEXT

This document is the source of truth for OralSense's dual-workflow structure: one platform, two workflows, a shared assessment engine, the 27-screen plan, and how every assessment is linked.

> On dual-workflow structure, this document wins over `SCREEN_INVENTORY.md`, `MASTER_PROMPT.md`, and earlier research-only wording. Scientific evidence, safety, non-diagnostic framing, and data-integrity rules in `PRODUCT_CONTEXT.md` still win over everything, including this document. `OPENAI_INTEGRATION.md` still governs the advisory quality-control layer.

Images supplied in chat when this context was written are visual references only. They are not screenshots of this implementation. Do not download or embed them.

---

## 1. One platform, two workflows

OralSense is **one platform** with two workflows:

1. **Clinical**
2. **Research**

These are not two applications, two products, or two codebases. Both workflows use the same assessment engine, the same trial record, and the same persistence rules.

The workflows differ in who the person is, what context an assessment belongs to, and how results are presented.

| | Clinical | Research |
|---|---|---|
| Person | Patient | Participant |
| Context | Visit | Study, protocol, and session |
| Sequence | Patient → Visit → Assessment → Results → Patient history | Participant → Study → Protocol → Session → Analysis |
| Purpose | Record measured sensory characteristics for a clinician to interpret | Produce reproducible, structured data |

---

## 2. Shared assessment engine

Protocol, trial recording, adaptive or fixed progression, quantitative analysis, uncertainty where the method supports it, quality review, and session history are one engine.

A clinical assessment and a research assessment run through that engine. The workflow chooses the person and the context. It does not fork the measurement method.

Adaptive progression is used when the selected protocol supports it. Otherwise the session follows the fixed protocol. The engine does not invent a second testing method to fit the workflow.

---

## 3. Clinical workflow

```text
Patient → Visit → Assessment → Results → Patient history
```

The clinician interprets the results and makes the diagnosis. OralSense does not diagnose, recommend treatment, or display a disease label.

Results are **measured sensory characteristics**: threshold and uncertainty only where the method supports them, trial-level observations, and advisory quality flags. A clinical report must not add claims the measurements do not support.

A clinical assessment links to a patient and a visit. It does not require a research project. Clinical visits are not forced into the research-study model.

---

## 4. Research workflow

```text
Participant → Study → Protocol → Session → Analysis
```

The focus is reproducible data: protocol version, session, trial-level records, analysis version, and export that a later analyst can trace.

Not every assessment belongs to a research study. An assessment that is part of a study links to that study, its protocol version, and the session. An assessment that is not part of a study is still valid when it links to the correct person and context.

---

## 5. Assessment linkage

Every assessment belongs to the correct **person** and **context**.

- **Person:** the patient (clinical) or the participant (research). Shared screens may say "person" when the same page serves both.
- **Context:** a clinical visit, or a research study and session. A clinical assessment may have a visit and no study.
- **Protocol:** the version actually used, including whether progression is adaptive or fixed.
- **Session history:** stored trials and prior sessions for that person, so later comparison does not require a new data model.

**Current adaptation requirement:** each future assessment links to the correct person, context, protocol, and session history. Later screens must be able to read that linkage. They must not require a redesign because early assessments were stored without it.

---

## 6. Screen plan

The planned product remains **27 screens**. This adaptation adds **zero mandatory new screens**.

A small workspace or context selector, or a clinical-visit form, may live inside an existing screen. Add a separate screen only if a later audit shows the existing page cannot hold the flow.

The inventory in `SCREEN_INVENTORY.md` is retained. Where its wording assumes a research-only application, this document governs.

### Screens 1–8 — existing foundation, adapted in place

Landing, sign-in, workspace setup, dashboard, directory, add person, profile, and assessment history already exist as the foundation. Adapt them in place so the same screens serve Clinical and Research. Do not duplicate them into a second app.

| # | Screen | Dual-workflow role |
|---|---|---|
| 1 | Landing | One product, both workflows. |
| 2 | Sign-in | Access to the shared workspace. |
| 3 | Workspace setup | Workspace and context, including which workflow is in use. |
| 4 | Dashboard | Overview for the active workflow. |
| 5 | Directory | Find the correct person (patient or participant). |
| 6 | Add person | Create the person record for the active workflow. |
| 7 | Profile | Person details and the contexts they belong to. |
| 8 | Assessment history | Prior sessions for that person. Clinical history is not a research study. |

### Screens 9–16 — shared assessment workflow

Both workflows use this path. Configuration must capture person, context, and protocol before testing starts.

| # | Screen | Role |
|---|---|---|
| 9 | Assessment selection | Start a new assessment or resume one. |
| 10 | Assessment configuration | Person, context (visit and/or study), modality, protocol version. A clinical assessment can omit a study. |
| 11 | Readiness | Procedure, materials, and prerequisites from the published protocol. Do not invent stimulus magnitudes or safety steps. |
| 12 | Active testing | Current trial, response controls, progress. The clinician or researcher administers the physical stimulus. |
| 13 | Progression | Adaptive next trial when the protocol supports it; otherwise the fixed protocol sequence. |
| 14 | Pause / resume | Recover a saved session without losing recorded trials. |
| 15 | Session review | Inspect trials and corrections before finalization. |
| 16 | Results | Calculated outcomes, uncertainty where justified, and quality indicators. Clinical reporting starts here and in history. |

Active testing and progression may share one route. Each state is designed; each does not need its own URL.

### Screens 17–20 — protocols and studies

Mostly research. Protocol management may also support clinical assessments, because a clinical visit still uses a versioned protocol.

| # | Screen | Role |
|---|---|---|
| 17 | Protocol library | Browse protocols available to the workspace. |
| 18 | Protocol details | Procedure, response types, parameters, requirements. |
| 19 | Protocol configuration and versioning | Configure a protocol and keep its versions. Historical sessions keep the version they used. |
| 20 | Study directory and study details | Research studies: participants, protocols, and assessments. Not a container for every clinical visit. |

### Screens 21–23 — analysis and advisory AI quality review

The same observations may support different presentations. A clinical report and a research analysis must not automatically make the same claims.

| # | Screen | Role |
|---|---|---|
| 21 | Trial-level analysis | Response patterns and the data behind calculated results. |
| 22 | AI quality review | Advisory flags for human review. It does not diagnose, change thresholds, or rewrite trials. |
| 23 | Longitudinal comparison | Compare compatible assessments for the same person across sessions. |

If AI quality review is unavailable, saved assessments and quantitative results remain available. The failure must not discard recorded work.

### Screens 24–25 — research analytics and exports

These screens are for research data. Exports carry privacy protections: minimum necessary fields, no unneeded identifiers, and no silent inclusion of clinical records that were not part of an authorized study export.

Clinical reporting starts in results (16) and assessment history (8). A separate clinical reporting screen is added only if later requirements justify it. It is not part of this adaptation.

### Screens 26–27 — workspace settings and recovery

Both workflows. Permission-aware: a person sees and changes only what that account is allowed to see and change. Hidden controls are not authorization.

| # | Screen | Role |
|---|---|---|
| 26 | Workspace settings | Account, workspace, and preferences for the shared platform. |
| 27 | Recovery states | Failed saves, interrupted sessions, unavailable AI review, empty results, and recoverable errors. |

Screen 27 is a set of designed states, not one ordinary page. AI unavailable must not lose saved work. A save is shown as saved only after the backend confirms it.

---

## 7. Safety and evidence boundaries

Unchanged, and not relaxed by the clinical workflow:

- OralSense does not diagnose, recommend treatment, or replace a clinician.
- No invented reference ranges, clinical cutoffs, or hard-coded medical values.
- No claim of clinical validation or clinical superiority.
- Prototype results are not clinical conclusions.
- Synthetic or simulated data, if used, is labeled as such and is not presented as patient data.
- Claims not supported by `PRODUCT_CONTEXT.md` or a cited paper are **unverified**.
