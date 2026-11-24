# ORALSENSE — MASTER PRODUCT CONTEXT

This file is the source of truth for OralSense's scientific evidence, safety boundaries, and product identity. Cursor rules and `AGENTS.md` are operational summaries of this document. If they conflict on those topics, this document wins.

> On product scope and UI timing, [MASTER_PROMPT.md](MASTER_PROMPT.md) supersedes §22 and §24: build the complete product rather than the "smallest" one, and treat UI/UX as a core requirement built with each screen rather than deferred. All scientific and safety rules here still apply.

---

## 1. PROJECT OVERVIEW

We are building **OralSense**, a software platform for standardized oral sensory assessment.

OralSense is intended for **clinicians and researchers**, not ordinary consumers.

The core problem is not that clinicians are physically incapable of performing oral sensory tests. They can perform many of these assessments manually.

The problem is that oral sensory assessment is **fragmented, heterogeneous, difficult to standardize, difficult to quantify consistently, and difficult to track longitudinally**.

OralSense should therefore NOT be positioned as:

- A generic patient-record app
- A digital replacement for pen and paper
- A symptom checker
- A diagnostic AI
- A smartphone that directly measures tongue sensation
- A medical device
- A replacement for clinicians
- An LLM chatbot

Instead, OralSense is an **assessment engine and digital workflow platform** that combines:

1. Standardized assessment protocols
2. Structured trial recording
3. Adaptive testing
4. Quantitative analysis
5. Uncertainty estimation
6. Response consistency / quality checks
7. Longitudinal patient/participant records
8. Structured research data
9. Exportable results

The physical sensory stimulus is still administered using appropriate existing testing procedures/equipment. OralSense records and analyzes the resulting observations.

---

## 2. THE SCIENTIFIC PROBLEM

Oral somatosensation includes multiple forms of sensory perception within the mouth, including tactile, pressure, thermal, and chemesthetic sensations.

Researchers and clinicians have developed multiple methods for measuring these different dimensions.

Examples include:

- Von Frey / monofilament-based tactile testing
- Pressure / point stimulation
- Spatial discrimination approaches
- Thermal detection/discrimination
- Chemesthetic testing
- Other specialized lingual/oral sensory methods

The important problem is that these methods are not unified into one comprehensive standardized assessment workflow.

Different studies may use different:

- Stimuli
- Equipment
- Protocols
- Trial structures
- Threshold definitions
- Recording methods
- Analysis approaches

This makes oral sensory assessment more difficult to reproduce, compare, and manage systematically.

OralSense addresses the **workflow and data problem surrounding these assessments**, not the underlying physical measurement itself.

---

## 3. KEY SCIENTIFIC EVIDENCE

### Evidence 1 — 2024 peer-reviewed review

A 2024 peer-reviewed review titled:

**“A review of assessment methods for measuring individual differences in oral somatosensory perception”**

examined existing approaches to measuring oral somatosensation.

- DOI: **10.1111/jtxs.12849**
- PMID: **38961563**

The review demonstrates substantial heterogeneity among oral somatosensory assessment methods and discusses the lack of a comprehensive method for assessing oral somatosensation as a whole. Tactile, thermal, and chemesthetic sub-modalities each have multiple procedures; a standardized protocol remains necessary for each method.

This is the primary scientific foundation for OralSense.

IMPORTANT:

Do not misrepresent the paper as saying:

> “There is no software for oral sensory testing.”

It does NOT prove that.

It supports the broader scientific problem of **heterogeneous and incomplete assessment methodologies**.

### Evidence 2 — 2026 lingual tactile sensitivity research

A July 2026 paper:

**“Evaluation of Lingual Tactile Sensitivity Using a Pneumatic Multi-Point Stimulation Device”**

PMID: **42522166**

developed a new pneumatic multi-point stimulation device for evaluating lingual tactile sensitivity.

The study is important because it demonstrates that researchers are still developing new ways of measuring tongue sensory function and that conventional sensory testing does not necessarily capture every aspect of lingual sensitivity.

The study also found differences in sensitivity that were not necessarily captured by conventional sensory approaches.

This supports the argument that oral sensory measurement is an active and incomplete research area.

Again, do NOT claim that the paper proves OralSense is necessary.

### Evidence 3 — 2025 taste/lingual tactile/chemesthetic research

A 2025 paper:

**“The taste of trigeminal sensations: relation between taste, lingual tactile acuity, and spicy perception in patients with taste dysfunction”**

PMID: **40434896**

examined relationships between taste dysfunction, lingual tactile acuity, and chemesthetic perception.

This supports the idea that oral sensory perception is multidimensional and that different sensory modalities can be meaningfully related.

This strengthens the rationale for considering oral sensory measurements as a structured profile rather than treating each test as an isolated number.

### Evidence 4 — lingual tactile sensitivity methodology

Research using methods such as Von Frey monofilaments has demonstrated that lingual tactile sensitivity can be experimentally measured using repeated trials and controlled procedures.

An example is the study associated with:

PMID **32150155**

and related 2020 work on lingual tactile sensitivity.

These studies demonstrate that oral sensory assessment can involve:

- Multiple trials
- Controlled stimulus presentation
- Participant responses
- Threshold estimation
- Experimental protocol
- Repeated measurements

This type of workflow is particularly suitable for structured digital recording and algorithmic analysis.

---

## 4. WHAT IS ACTUALLY PROVEN VS WHAT IS NOT

This distinction is extremely important.

### Strongly supported

- Oral somatosensory assessment is scientifically established.
- Multiple assessment methodologies exist.
- Existing methods are heterogeneous.
- Different methods measure different sensory dimensions.
- Standardization remains an issue.
- Lingual/oral sensory measurement is still an active research area.
- Researchers continue developing new measurement techniques.
- Oral sensory assessment can involve repeated trials and quantitative thresholds.

### NOT YET PROVEN

- That no digital software currently exists for any oral sensory test.
- That every clinician currently uses pen and paper.
- That clinicians are desperate for OralSense.
- That OralSense improves clinical outcomes.
- That OralSense can diagnose diseases.
- That OralSense is clinically validated.
- That OralSense is a medical device.
- That OralSense is already superior to all existing workflows.

Never invent evidence for these claims.

If additional research is required, explicitly identify the claim as **unverified** rather than making it up.

---

## 5. THE CORE SOLUTION

OralSense turns oral sensory testing into a structured digital workflow.

The software should provide:

### A. Standardized protocols

A clinician/researcher selects an assessment protocol.

The software presents the standardized sequence and records the relevant information consistently.

### B. Trial-level recording

Each trial should be stored as structured data.

For example:

```text
Participant ID
Assessment ID
Modality
Trial number
Stimulus level
Participant response
Timestamp
Protocol version
```

Do not hard-code arbitrary medical values without scientific justification.

---

## 6. ADAPTIVE TESTING

Adaptive testing is one of the most important technical components.

Instead of blindly performing a large fixed number of trials, the system can use previous responses to determine which next measurement would be most informative.

Conceptually:

```text
Stimulus
   ↓
Participant response
   ↓
Update estimate
   ↓
Choose next informative stimulus
   ↓
Participant response
   ↓
Update estimate
   ↓
Repeat
```

The goal is to efficiently estimate a sensory threshold while quantifying uncertainty.

This can be implemented using appropriate psychophysical/statistical methods.

Potential approaches include:

- Bayesian adaptive estimation
- Staircase procedures
- Threshold estimation
- Sequential decision logic

Do NOT claim that an algorithm is clinically superior unless experimentally validated.

For the hackathon, the adaptive engine should be presented as a **technical prototype demonstrating the concept**, not as clinically validated software.

---

## 7. ANALYSIS ENGINE

After testing, OralSense should transform trial-level data into meaningful quantitative results.

Potential outputs:

- Estimated threshold
- Confidence/credible interval or uncertainty estimate
- Number of trials
- Response consistency
- Protocol information
- Modality-specific result
- Quality-control indicators

Example:

```text
TACTILE ASSESSMENT

Estimated threshold: 34.8 units
Uncertainty: ± X units
Trials: 12
Consistency: High
Protocol: XYZ
```

The exact mathematical method must be scientifically justified.

Do NOT fabricate medical reference ranges.

---

## 8. ORAL-SENSORY PROFILE

OralSense can organize results into a multidimensional profile:

```text
                 ORAL SENSORY PROFILE

Tactile          █████████
Thermal          ███████
Chemesthetic     ██████████
```

The profile is a structured representation of measurements.

It is NOT a diagnosis.

Never display:

> “Patient has disease X.”

unless there is a scientifically validated and explicitly approved clinical model supporting such a claim.

The safe framing is:

> “Measured sensory characteristics”

rather than:

> “Diagnosis.”

---

## 9. PATIENT / PARTICIPANT WORKFLOW

There are two important roles.

### Role 1 — Clinician / Researcher

This is the primary user of OralSense.

### Role 2 — Patient / Research Participant

The participant receives the physical sensory stimulus and provides the response.

The participant does NOT need to operate the app.

---

## 10. COMPLETE CLINICIAN WORKFLOW

### FIRST VISIT

```text
Clinician opens OralSense
        ↓
Patients / Participants
        ↓
Add New Patient
        ↓
Create basic profile
        ↓
Start Assessment
        ↓
Choose sensory assessment
        ↓
Choose protocol
        ↓
Run trials
        ↓
Clinician administers appropriate physical stimulus
        ↓
Clinician records participant response
        ↓
Adaptive engine determines next trial
        ↓
Repeat
        ↓
Assessment completed
        ↓
Analysis engine calculates results
        ↓
Generate oral-sensory profile
        ↓
Save assessment
```

### FUTURE VISIT

```text
Open OralSense
        ↓
Patients / Participants
        ↓
Select existing patient
        ↓
View previous assessments
        ↓
Start new assessment
        ↓
Run same or appropriate protocol
        ↓
Generate new result
        ↓
Compare with historical measurements
        ↓
Save to longitudinal history
```

---

## 11. RESEARCHER WORKFLOW

For research use:

```text
Create study
      ↓
Define protocol
      ↓
Add participants
      ↓
Run assessments
      ↓
Store trial-level data
      ↓
Analyze measurements
      ↓
Export structured dataset
```

The platform should make it possible to preserve structured trial-level information rather than only storing a final number.

This is important for reproducibility and downstream research.

---

## 12. DEMO WORKFLOW

The hackathon demo should NOT require us to physically test someone's tongue.

The safest and cleanest demonstration is:

```text
Load published/raw dataset
        ↓
Display raw trial-level measurements
        ↓
Run OralSense analysis engine
        ↓
Calculate threshold
        ↓
Calculate uncertainty
        ↓
Generate sensory profile
        ↓
Compare against legitimate reference/reported result
```

If suitable participant-level/raw data cannot be obtained:

Use clearly labeled synthetic data.

Example label:

> “Synthetic validation dataset generated using published test parameters. Demonstrates the analysis engine and adaptive workflow; this is not clinical validation.”

Never pretend synthetic data is real patient data.

---

## 13. VALIDATION PHILOSOPHY

The strongest validation is:

```text
Published raw/participant-level data
             ↓
       OralSense
             ↓
      Independent result
             ↓
Compare with published result
```

Do NOT:

```text
Read paper's final answer
       ↓
Design algorithm to reproduce it
       ↓
Claim validation
```

That would be circular and scientifically weak.

If no appropriate public dataset exists, state the limitation honestly.

---

## 14. WHAT MAKES ORALSENSE DIFFERENT FROM PEN AND PAPER?

This is a critical judging issue.

Do NOT claim:

> “Doctors cannot do this manually.”

They can.

Do NOT claim:

> “Doctors need an app because paper is impossible.”

They do not.

Instead, the software advantage comes from combining:

1. **Adaptive testing** — The algorithm can dynamically select the next informative trial.
2. **Automated quantitative analysis** — Thresholds and uncertainty can be calculated automatically.
3. **Standardized execution** — Protocols can be encoded into the workflow rather than relying entirely on manual execution.
4. **Structured trial-level data** — Every trial can be stored consistently.
5. **Quality control** — The system can identify inconsistent or potentially unreliable response patterns.
6. **Longitudinal comparison** — Results from multiple visits can be compared automatically.
7. **Research datasets** — Large collections of assessments can be exported in structured form.

Therefore:

> **OralSense is not “paper on a phone.” It is an assessment engine.**

That distinction must be obvious during the demo.

---

## 15. WHAT MAKES ORALSENSE DIFFERENT FROM A SPREADSHEET?

A spreadsheet can store data.

However, OralSense should combine:

```text
Protocol
+
Trial engine
+
Adaptive algorithm
+
Analysis
+
Quality control
+
Patient/participant history
+
Research data structure
```

The strongest technical component is the **adaptive assessment engine**.

If the implementation becomes nothing more than forms + database + charts, the product becomes significantly weaker.

---

## 16. AI STRATEGY

Do NOT make OralSense an LLM chatbot.

The intelligence should come from the assessment itself.

Potential computational intelligence:

- Bayesian inference
- Psychophysical modeling
- Adaptive trial selection
- Statistical threshold estimation
- Uncertainty estimation
- Anomaly / consistency detection
- Optional machine-learning analysis later

If ML is used, it must have a real purpose.

Never add AI simply because the hackathon theme contains AI.

A strong explanation is:

> “The intelligence in OralSense is used to optimize measurement and analyze sensory responses, rather than generate medical advice.”

### OpenAI quality-control layer

OralSense has two separate intelligence components. The full, binding spec is [OPENAI_INTEGRATION.md](OPENAI_INTEGRATION.md).

1. **Adaptive assessment**: deterministic/statistical/psychophysical. It selects trials and never depends on OpenAI.
2. **AI quality control**: the OpenAI API, called server-side once per completed assessment, after local quantitative analysis. It reviews the structure and consistency of the recorded trials and returns structured, advisory flags for clinician/researcher review.

The OpenAI layer never diagnoses, recommends treatment, or changes the threshold, uncertainty, or raw trial data. If it is unavailable, the assessment and its quantitative results remain fully available.

Hackathon positioning: **an AI-assisted oral sensory assessment platform**. “The AI assists with assessment optimization and measurement-quality review.”

---

## 17. SAFETY BOUNDARIES

OralSense must NOT:

- Diagnose disease
- Recommend treatment
- Replace clinicians
- Claim clinical validation without evidence
- Direct users to perform unsafe oral experiments
- Recommend dangerous chemical/thermal stimuli
- Pretend a phone can physically measure sensation
- Invent medical reference ranges
- Present experimental results as clinical conclusions

Physical testing should rely on appropriate established protocols/equipment.

For the hackathon, simulated or previously collected data is preferable to creating unsafe physical testing procedures.

---

## 18. DSH HACKS JUDGING STRATEGY

Official DSH Hacks V2 judging criteria (verified against [the current Devpost page](https://dsh-hacks-v2.devpost.com/)):

- **Idea** — Did the proposal address the problem statement and theme? Was the idea innovative? How much potential impact could this proposal have if deployed to the public?
- **Implementation** — Does the solution work? Did the team achieve everything they wanted? How technically challenging/impressive was the implementation?
- **Design** — Did the team put thought into the user experience? How well designed is the interface?
- **Presentation** — Does the presentation clearly define and address the problem statement?

Theme: **AI × Healthcare**. A working software solution is required, not a pitch-only submission. Deadline: **14 November 2026**.

Judges score **Design**, but OralSense must still **not start with aesthetics**. Establish the assessment engine first. UX becomes a scored obligation after the engine is real, not a reason to lead with branding.

### PROBLEM SIGNIFICANCE (Idea)

Strong if we demonstrate:

- Real scientific problem
- Published evidence
- Specific affected users
- Clear workflow difficulty
- Existing methodological fragmentation

Weak if the pitch is:

> “Doctors still use paper.”

### INNOVATION (Idea / Implementation)

Strong if:

- Adaptive testing is technically meaningful.
- Multiple oral sensory modalities are unified.
- Protocol + measurement + analysis are integrated.
- The system creates structured longitudinal/research data.

Weak if:

- It is just CRUD.
- It is just a patient database.
- It is just a chatbot.
- It is just a dashboard.

### TECHNICAL DEPTH (Implementation)

Important components:

```text
Protocol Engine
      ↓
Trial Engine
      ↓
Adaptive Testing Engine
      ↓
Analysis Engine
      ↓
Profile Engine
      ↓
Longitudinal Data
```

The exact architecture should remain modular and understandable.

### AI / INTELLIGENCE

The algorithm should solve a real computational problem:

> How can we choose informative measurements and estimate a participant's sensory threshold efficiently and quantitatively?

This is much stronger than:

> “We use an LLM to explain the results.”

### IMPACT

Potential users:

- Oral sensory researchers
- Clinical researchers
- Dentists / oral-health researchers where appropriate
- Sensory science laboratories
- Research institutions

Potential impact:

- More reproducible assessments
- Better structured data
- Easier longitudinal comparison
- More efficient experimental workflows
- Better research data organization

Do NOT claim improved patient outcomes until validated.

### FEASIBILITY

The hackathon prototype should focus on the software layer.

We do NOT need to manufacture:

- Sensory probes
- Pneumatic devices
- Thermal devices
- Medical hardware

We can demonstrate the digital assessment and analysis layer using appropriate existing protocols and datasets.

### DEMOABILITY

The product should have a visually understandable technical story:

```text
RAW TRIALS
     ↓
ORALSENSE ADAPTIVE ENGINE
     ↓
THRESHOLD + UNCERTAINTY
     ↓
SENSORY PROFILE
     ↓
LONGITUDINAL COMPARISON
```

A judge should be able to understand the technical value by watching the algorithm operate.

---

## 19. CORE PRODUCT STATEMENT

The strongest concise description is:

> **OralSense is a digital platform that standardizes and analyzes oral sensory assessments by combining structured protocols, adaptive testing, quantitative threshold estimation, and longitudinal sensory profiles.**

Alternative:

> **OralSense turns fragmented oral sensory testing into a standardized, adaptive, quantitative digital workflow.**

Do not describe it as a diagnostic tool.

---

## 20. THE CENTRAL PROBLEM STATEMENT

Use this logic:

> Oral sensory function can be measured through multiple specialized methods, but existing approaches are heterogeneous and assess different dimensions using different protocols and measurement strategies. This makes standardized, reproducible, quantitative assessment and longitudinal comparison difficult. OralSense provides a unified digital assessment layer that standardizes the workflow, adaptively manages trials, analyzes responses, and preserves structured longitudinal data.

---

## 21. THE CENTRAL DIFFERENTIATOR

The core differentiator is:

> **OralSense is not merely recording oral sensory results; it is computationally managing the assessment itself.**

The software should actively:

- Guide the protocol
- Select informative trials
- Process responses
- Estimate thresholds
- Quantify uncertainty
- Check consistency
- Build structured profiles
- Preserve longitudinal data

That is the product.

---

## 22. WHAT NOT TO BUILD YET

Do NOT spend development time first on:

- UI aesthetics
- Color palettes
- Animations
- Branding
- Logo design
- Marketing landing pages
- Fancy dashboards
- Cosmetic components

Those are intentionally outside this context until the engine is solid.

First establish:

1. Scientific validity
2. Exact assessment workflow
3. Protocol representation
4. Adaptive algorithm
5. Analysis mathematics
6. Data model
7. Validation strategy
8. Research evidence
9. Technical feasibility
10. Hackathon differentiation

Only after those are solid should design/UX become a major focus. Design is a scored DSH criterion, so it must come later — not never.

---

## 23. CURSOR'S ROLE

When working on OralSense, behave as a **technical product engineer + research-aware developer**, not merely a code generator.

Before implementing a feature:

1. Identify what scientific/problem assumption it depends on.
2. Check whether that assumption is supported.
3. Do not invent medical facts.
4. Keep clinical claims conservative.
5. Prefer transparent algorithms over black-box AI where appropriate.
6. Keep the architecture modular.
7. Make every computational result explainable.
8. Separate prototype functionality from clinically validated functionality.
9. Never fake datasets or validation.
10. Never claim a feature is medically accurate unless evidence supports it.

If a proposed feature does not contribute meaningfully to the core assessment problem, question whether it should exist.

---

## 24. MOST IMPORTANT PRINCIPLE

**Build the smallest technically impressive product that genuinely solves the documented workflow problem.**

Do not build:

> “A healthcare app with AI.”

Build:

> **“A computational assessment engine for standardized oral sensory measurement.”**

That is the identity of OralSense.

---

## 25. FIRST PROTOTYPE INTENT (LOCKED)

The first prototype should implement **all three modalities** — tactile, thermal, and chemesthetic — with **real (even if simplified) trial engines**.

The oral-sensory profile must be a structured representation of actual modality results, **not a stub**.

Each modality may use a simplified but scientifically defensible protocol (for example, point-pressure / staircase-style tactile trials; thermal detection or discrimination trials; localized or whole-mouth chemesthetic trials). Do not invent stimulus magnitudes, reference ranges, or clinical cutoffs.

Demo data must be published raw data if obtainable, otherwise **clearly labeled synthetic data** generated from published test parameters. Never present synthetic data as real patient data.
