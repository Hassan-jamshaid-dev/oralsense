# OralSense — Agent Constitution

Source of truth: [docs/PRODUCT_CONTEXT.md](docs/PRODUCT_CONTEXT.md). If this file conflicts with that document, the product context wins.

Behave as a **technical product engineer + research-aware developer**, not a code generator.

Project owner and author: **Muhammad Hassan Jamshaid**. You are not the autonomous product owner.

Related binding specs:

- [docs/ENGINEERING_CONTEXT.md](docs/ENGINEERING_CONTEXT.md): engineering process, stack, security, data integrity, testing, performance, git and authorship rules.
- [docs/OPENAI_INTEGRATION.md](docs/OPENAI_INTEGRATION.md): the OpenAI quality-control layer.
- [docs/SCREEN_INVENTORY.md](docs/SCREEN_INVENTORY.md): proposed 27-screen web app inventory, navigation, and build phases. Build only what the owner asks for; its open questions are unresolved.
- [docs/DUAL_WORKFLOW_CONTEXT.md](docs/DUAL_WORKFLOW_CONTEXT.md): one platform, two workflows (Clinical and Research), shared assessment engine, 27 screens with no mandatory extra screen, and the assessment linkage rule.
- [docs/MASTER_PROMPT.md](docs/MASTER_PROMPT.md): full product scope, stack, design system and palette, UI/UX direction, testing, deployment, definition of done.

**Precedence when documents disagree:**

1. Scientific evidence, safety, non-diagnostic framing, and data-integrity rules (`PRODUCT_CONTEXT.md`, `OPENAI_INTEGRATION.md`, `ENGINEERING_CONTEXT.md` §13–§17, §53–§57) are never relaxed by any later document.
2. On product scope, stack, UI/UX, testing depth, CI, and deployment, `MASTER_PROMPT.md` (newest) supersedes earlier documents. Specifically: build the full product rather than the "smallest" product; use Tailwind, Recharts, and Lucide (not plain CSS); keep testing focused; configure no CI/CD.
3. On dual-workflow structure (clinical vs research, shared engine, screen plan, assessment linkage), `DUAL_WORKFLOW_CONTEXT.md` wins. Scientific and safety rules in `PRODUCT_CONTEXT.md` still win over everything.

Never commit or push unless explicitly asked. Never credit Cursor or any AI as an author.

---

## Identity

OralSense is a **computational assessment engine** for standardized oral sensory measurement.

It is for **clinicians and researchers**, not consumers. The participant receives the physical stimulus and responds; they do not operate the app.

Use this description:

> OralSense is a digital platform that standardizes and analyzes oral sensory assessments by combining structured protocols, adaptive testing, quantitative threshold estimation, and longitudinal sensory profiles.

OralSense is **not**: a generic EHR, paper-on-a-phone, symptom checker, diagnostic AI, medical device, clinician replacement, smartphone that measures tongue sensation, or an LLM chatbot.

The physical stimulus is administered with existing procedures/equipment. OralSense records, adaptively manages, and analyzes observations.

Differentiator: **it computationally manages the assessment itself** (protocol, next trial, threshold, uncertainty, QC, profile, longitudinal data). It is not forms + database + charts.

---

## Problem (use this logic)

Oral sensory function can be measured through multiple specialized methods, but existing approaches are heterogeneous and assess different dimensions using different protocols and measurement strategies. This makes standardized, reproducible, quantitative assessment and longitudinal comparison difficult. OralSense provides a unified digital assessment layer that standardizes the workflow, adaptively manages trials, analyzes responses, and preserves structured longitudinal data.

Do **not** pitch “doctors still use paper” or “doctors cannot do this manually.” They can. The value is adaptive testing, quantitative analysis, standardized execution, trial-level data, quality control, longitudinal comparison, and research export.

---

## Evidence boundaries

Cite only supported claims. If a claim is not supported, label it **unverified**. Never invent evidence, clinical outcomes, or “clinicians are desperate.”

**Supported:** oral somatosensory assessment exists; methods are heterogeneous; different methods measure different dimensions; standardization is an issue; the field is active; assessments can involve repeated trials and thresholds.

**Not proven:** no software exists; everyone uses paper; OralSense improves outcomes; OralSense diagnoses disease; OralSense is clinically validated; OralSense is a medical device; OralSense is superior to existing workflows.

Primary evidence:

| Paper | ID | Use for | Do not claim |
|---|---|---|---|
| 2024 review of oral somatosensory assessment methods | DOI 10.1111/jtxs.12849, PMID 38961563 | Heterogeneity; no comprehensive standardized method | “There is no software for oral sensory testing.” |
| 2026 pneumatic multi-point lingual tactile device | PMID 42522166 | Measurement is still an active, incomplete research area | That the paper proves OralSense is necessary |
| 2025 taste / lingual tactile / chemesthesis relations | PMID 40434896 | Multidimensional profile rationale | Diagnosis of taste dysfunction |
| Von Frey / lingual tactile trial methodology | PMID 32150155 | Repeated trials, threshold estimation, structured recording | Clinical validation of OralSense |

---

## Safety and claims

Never:

- Diagnose disease or display “Patient has disease X”
- Recommend treatment
- Claim clinical validation without evidence
- Invent medical reference ranges or hard-code arbitrary medical values
- Direct users to perform unsafe oral experiments or dangerous chemical/thermal stimuli
- Pretend a phone physically measures sensation
- Present prototype results as clinical conclusions
- Fake datasets or circular “validation” (fitting an algorithm to a paper’s final number)

Frame results as **measured sensory characteristics**, not diagnosis.

Prototype vs validated: the hackathon adaptive engine is a **technical prototype demonstrating the concept**, not clinically validated software. Do not claim an algorithm is clinically superior unless experimentally validated.

Synthetic data, if used, must be labeled, for example:

> Synthetic validation dataset generated using published test parameters. Demonstrates the analysis engine and adaptive workflow; this is not clinical validation.

---

## Architecture (keep modular)

```text
Protocol Engine → Trial Engine → Adaptive Testing Engine
      → Analysis Engine → Profile Engine → Longitudinal Data
```

Every computational result must be explainable. Prefer transparent psychophysical/statistical methods over black-box AI.

**Intelligence** solves: *how to choose informative measurements and estimate a sensory threshold efficiently and quantitatively.* Not: an LLM chatbot or anything that gives medical advice.

There are two separate intelligence components (full spec: [docs/OPENAI_INTEGRATION.md](docs/OPENAI_INTEGRATION.md)):

1. **Adaptive assessment**: deterministic/statistical. Selects trials. Never uses OpenAI.
2. **AI quality control**: OpenAI, called from the FastAPI backend once per completed assessment, after local analysis. It flags unusual or inconsistent response patterns for human review. Its output is advisory only: it never changes thresholds, uncertainty, or trial data, and never diagnoses. If it fails, the assessment still works.

Allowed computational methods: Bayesian adaptive estimation, staircases, threshold estimation, sequential decision logic, uncertainty, consistency/QC checks. Optional ML only if it has a real purpose.

Trial records should include at least: participant ID, assessment ID, modality, trial number, stimulus level, participant response, timestamp, protocol version.

---

## First prototype intent

Implement **tactile, thermal, and chemesthetic** with **real (simplified) trial engines**. The oral-sensory profile is a structured representation of those results, **not a stub**.

Do not invent stimulus magnitudes, reference ranges, or clinical cutoffs. Justify protocol choices from published methods.

Demo path: load published/raw or clearly labeled synthetic trial data → show raw trials → run adaptive/analysis engine → threshold + uncertainty → profile → optional longitudinal comparison. Do **not** require physically testing someone’s tongue.

Validation: independent analysis of published raw data vs published result. If no public dataset exists, say so. Never design the algorithm to reproduce a paper’s final answer and call it validation.

---

## Workflows to preserve

**Clinician:** add/select participant → choose modality and protocol → administer physical stimulus → record response → adaptive next trial → analysis → profile → save; later visits compare history.

**Researcher:** study → protocol → participants → assessments → trial-level storage → analysis → structured export.

---

## DSH Hacks V2

Official criteria: **Idea, Implementation, Design, Presentation**. Theme: AI × Healthcare. Working software required. Deadline: 14 November 2026.

Scientific validity, protocol, adaptive math, analysis, data model, and validation come before visual polish. UI/UX is still a core requirement, built with each screen using the design system, not a final cosmetic pass. Landing and marketing pages come late.

Build the **complete, hackathon-ready product** (`docs/MASTER_PROMPT.md`), and keep it a computational assessment engine, not “a healthcare app with AI.” Simplify the stack, testing, and deployment, never the product.

---

## Before implementing any feature

1. Identify the scientific/problem assumption.
2. Check whether it is supported in `docs/PRODUCT_CONTEXT.md`.
3. Do not invent medical facts.
4. Keep clinical claims conservative.
5. Prefer transparent algorithms.
6. Keep modules separate.
7. Make results explainable.
8. Separate prototype from clinically validated.
9. Never fake data or validation.
10. Drop features that do not serve the core assessment problem.
