# ORALSENSE — OPENAI API INTEGRATION CONTEXT

## IMPORTANT

Store this entire document as persistent project context for the OralSense project.

This is a product/architecture requirement, not a temporary implementation suggestion.

Do NOT reinterpret or remove these requirements unless explicitly instructed.

---

# 1. PRODUCT CONTEXT

OralSense is a web-based oral sensory assessment platform for clinicians and researchers.

The core product is:

> A digital platform that standardizes and analyzes oral sensory assessments by combining structured protocols, adaptive assessment, quantitative analysis, quality control, and longitudinal records.

OralSense is NOT:

* A diagnostic tool
* A symptom checker
* A replacement for clinicians
* A consumer medical app
* A smartphone that physically measures oral sensation
* An LLM chatbot

The physical sensory stimulus is administered using an appropriate existing procedure/equipment. OralSense records and analyzes the resulting observations.

---

# 2. AI STRATEGY

OralSense has TWO AI/intelligence components.

## AI COMPONENT 1 — ADAPTIVE ASSESSMENT

This is the core computational intelligence.

It determines which trial/stimulus should be performed next based on previous responses.

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

This component should NOT depend on the OpenAI API.

It should use a deterministic/statistical/psychophysical algorithm so that:

* Results are reproducible
* The algorithm is explainable
* The system does not depend on an external LLM
* The assessment does not randomly change because an LLM generated a different answer
* The measurement process remains scientifically defensible

Potential implementation approaches can include appropriate adaptive threshold-estimation/statistical methods.

DO NOT invent a medical algorithm.

DO NOT claim clinical validity without validation.

---

# 3. AI COMPONENT 2 — AI QUALITY CONTROL

This is where the **OpenAI API belongs**.

After the assessment has collected enough trial data and the quantitative analysis has been performed, OralSense should send a carefully structured representation of the assessment to an OpenAI model.

The OpenAI model's job is:

> Analyze the STRUCTURE AND CONSISTENCY of the recorded assessment and identify potentially unreliable or unusual response patterns for clinician/researcher review.

The OpenAI model is NOT allowed to:

* Diagnose a disease
* Diagnose a patient
* Recommend treatment
* Determine whether a patient is medically healthy/unhealthy
* Override the quantitative analysis
* Modify the threshold calculation
* Choose medical treatment
* Invent missing measurements
* Invent reference ranges
* Make unsupported clinical claims

The model is assisting with **measurement-quality review**, not clinical decision-making.

---

# 4. EXACT OPENAI API LOCATION

The OpenAI API should be called ONLY AFTER the assessment's trial data has been collected and the local analysis has been completed.

The intended flow is:

```text
Clinician
   ↓
Start Assessment
   ↓
Protocol Engine
   ↓
Trial Collection
   ↓
Adaptive Assessment Engine
   ↓
Final Trial Dataset
   ↓
LOCAL QUANTITATIVE ANALYSIS
   ↓
Threshold / uncertainty / response metrics
   ↓
OPENAI QUALITY-CONTROL ANALYSIS
   ↓
Structured QC result
   ↓
Clinician sees assessment + QC
```

The OpenAI API should therefore NOT be called:

* On every button click
* After every trial
* To choose the next stimulus
* To calculate the sensory threshold
* To replace the adaptive engine
* Directly from arbitrary frontend components

The API should be called **once per completed assessment**, or only when the clinician explicitly requests a quality review.

---

# 5. BACKEND REQUIREMENT

The OpenAI API key MUST NEVER be placed in the frontend.

NEVER do this:

```text
React frontend
    ↓
OpenAI API directly
```

Instead:

```text
React frontend
      ↓
FastAPI backend
      ↓
OpenAI API
```

The API key must exist only on the server.

Use an environment variable such as:

```text
OPENAI_API_KEY=...
```

Never hard-code the key.

Never commit `.env` files containing secrets.

Never expose the key through frontend JavaScript.

Never return the API key to the browser.

---

# 6. RECOMMENDED BACKEND ARCHITECTURE

Keep the OpenAI integration isolated.

Conceptually:

```text
backend/
│
├── api/
│   └── assessment_routes
│
├── services/
│   ├── adaptive_engine
│   ├── analysis_engine
│   ├── quality_control_service
│   └── openai_service
│
├── models/
│   ├── patient
│   ├── assessment
│   └── trial
│
└── config/
    └── settings
```

The exact project structure can differ depending on the existing codebase.

The important architectural principle is:

> OpenAI integration must be isolated behind a service layer.

Do NOT scatter OpenAI API calls throughout React components or backend route handlers.

---

# 7. OPENAI SERVICE RESPONSIBILITY

Create a dedicated service responsible for communicating with OpenAI.

Conceptually:

```text
quality_control_service
        ↓
openai_service
        ↓
OpenAI API
```

The quality-control service should prepare the structured assessment data.

The OpenAI service should:

1. Receive sanitized structured data.
2. Construct the appropriate request.
3. Call the OpenAI API.
4. Require structured output.
5. Validate the returned structure.
6. Return the validated result to the quality-control service.
7. Handle API failures safely.

---

# 8. DATA SENT TO OPENAI

Do NOT send unnecessary patient information.

The OpenAI model does not need:

* Patient name
* Address
* Phone number
* Email
* National ID
* Date of birth
* Other unnecessary personally identifying information

Prefer a pseudonymous assessment ID.

Example:

```json
{
  "assessment_id": "A-1042",
  "modality": "tactile",
  "protocol": "example_protocol_v1",
  "trials": [
    {
      "trial": 1,
      "stimulus_level": 30,
      "response": "not_detected"
    },
    {
      "trial": 2,
      "stimulus_level": 45,
      "response": "detected"
    }
  ],
  "analysis": {
    "estimated_threshold": 38.7,
    "uncertainty": 2.1,
    "trial_count": 12
  }
}
```

Use only the minimum information necessary for quality-control analysis.

---

# 9. OPENAI OUTPUT MUST BE STRUCTURED

Do NOT ask the model for free-form paragraphs and then attempt to parse arbitrary text.

Require a structured response.

Conceptual output:

```json
{
  "quality_status": "good",
  "confidence": "moderate",
  "flags": [
    {
      "trial": 8,
      "type": "inconsistent_response_pattern",
      "reason": "Response pattern differs from surrounding trials."
    }
  ],
  "summary": "The assessment appears internally consistent overall, with one trial pattern worth reviewing.",
  "review_recommended": true
}
```

The exact schema can be refined during implementation.

The backend must validate the response before sending it to the frontend.

If the response does not match the expected schema, treat it as an API failure rather than trusting malformed output.

---

# 10. IMPORTANT: OPENAI DOES NOT DETERMINE THE MEDICAL RESULT

This distinction is mandatory.

The quantitative analysis engine determines:

```text
Estimated threshold
Uncertainty
Trial count
Other mathematical measurements
```

The OpenAI quality-control layer determines only:

```text
Potential inconsistencies
Potential data-quality concerns
Patterns worth reviewing
Structured explanation of those flags
```

The LLM must NEVER change:

```text
estimated_threshold
uncertainty
raw_trial_data
protocol
stimulus_level
participant_response
```

The OpenAI output is advisory.

---

# 11. EXAMPLE

Suppose OralSense records:

```text
Trial 1 → 20 → Not detected
Trial 2 → 30 → Not detected
Trial 3 → 40 → Detected
Trial 4 → 35 → Detected
Trial 5 → 32 → Not detected
Trial 6 → 34 → Detected
Trial 7 → 33 → Not detected
```

The local analysis engine calculates:

```text
Estimated threshold = 33.8
Uncertainty = X
```

Then the OpenAI quality-control layer receives the structured trial information.

It might return:

```text
Quality status: Good

Flag:
Trial 4 should be reviewed because its response pattern is unusual relative to neighboring measurements.

Review recommended: Yes
```

The LLM does NOT change the threshold to 35.

It does NOT diagnose the participant.

It simply flags the data for human review.

---

# 12. WHY USE OPENAI HERE?

The OpenAI API is being used because language models can help interpret complex structured patterns and communicate potential data-quality concerns clearly to the clinician/researcher.

However, the system should NOT pretend that the LLM is mathematically superior to the statistical analysis.

The architecture deliberately separates:

### Deterministic scientific computation

from

### AI-assisted interpretation/quality review

This makes the system safer and more explainable.

---

# 13. ERROR HANDLING

If OpenAI is unavailable:

```text
OpenAI API unavailable
        ↓
Assessment remains valid
        ↓
Quantitative results still available
        ↓
QC status:
"AI quality review unavailable"
```

Do NOT prevent the clinician from accessing the completed assessment simply because the OpenAI API failed.

The core product must continue functioning without the LLM.

---

# 14. COST / PERFORMANCE

Do NOT call the API unnecessarily.

Bad:

```text
Trial 1 → API
Trial 2 → API
Trial 3 → API
Trial 4 → API
...
```

Good:

```text
12 trials
   ↓
Local analysis
   ↓
ONE structured OpenAI QC request
```

This minimizes:

* API cost
* latency
* rate-limit issues
* unnecessary data transmission

---

# 15. PRIVACY

Treat assessment information as sensitive.

Before sending anything to OpenAI:

1. Remove unnecessary identifiers.
2. Send only required assessment information.
3. Never send credentials or secrets.
4. Never send unrelated patient information.
5. Keep API keys server-side.
6. Log only what is necessary for debugging.
7. Avoid logging full sensitive assessment payloads unnecessarily.

The prototype should use synthetic/demo data whenever possible.

---

# 16. HACKATHON POSITIONING

OralSense should be described as:

> **An AI-assisted oral sensory assessment platform.**

The AI story:

### AI #1

Adaptive assessment intelligently selects informative trials.

### AI #2

OpenAI-powered quality control reviews completed trial patterns for potential inconsistencies and flags them for clinician/researcher review.

This gives OralSense a meaningful AI component without making the entire healthcare product dependent on an LLM.

---

# 17. DO NOT OVERSELL

Never say:

> “Our AI diagnoses oral sensory disorders.”

Never say:

> “GPT determines whether the patient is healthy.”

Never say:

> “OpenAI validates the patient's medical condition.”

Never say:

> “The AI replaces the clinician.”

Correct language:

> “The AI assists with assessment optimization and measurement-quality review.”

---

# 18. DEVELOPMENT PRIORITY

Build in this order:

### Phase 1

Working assessment workflow.

### Phase 2

Trial storage.

### Phase 3

Adaptive assessment engine.

### Phase 4

Quantitative analysis.

### Phase 5

Quality-control engine.

### Phase 6

OpenAI API integration.

### Phase 7

Validation and testing.

Do not integrate the OpenAI API before the underlying assessment workflow works.

---

# 19. CURSOR IMPLEMENTATION RULE

Before writing code for the OpenAI integration:

1. Inspect the existing OralSense codebase.
2. Identify the current frontend/backend architecture.
3. Identify where assessment completion is handled.
4. Identify the existing assessment/trial data model.
5. Identify the existing analysis engine.
6. Determine the smallest clean integration point.
7. Do NOT rewrite unrelated parts of the application.
8. Do NOT create duplicate services.
9. Do NOT add unnecessary dependencies.
10. Do NOT expose secrets.

Then implement the OpenAI integration as a clean, isolated service.

---

# 20. FINAL PRODUCT ARCHITECTURE

The intended architecture is:

```text
                    ORALSENSE
                        │
                        ▼
               Assessment Protocol
                        │
                        ▼
                 Trial Collection
                        │
                        ▼
              Adaptive Assessment AI
                        │
                        ▼
               Completed Trial Data
                        │
                        ▼
              Quantitative Analysis
                        │
                 ┌──────┴──────┐
                 ▼             ▼
          Threshold /       Uncertainty
           Results
                 │
                 ▼
          AI Quality Control
                 │
                 ▼
           OpenAI API
                 │
                 ▼
       Structured QC Flags
                 │
                 ▼
        Clinician / Researcher
                 │
                 ▼
          Final Assessment
                 │
                 ▼
       Longitudinal Patient /
        Researcher History
```

## NON-NEGOTIABLE SUMMARY

**OpenAI API = Quality Control layer.**

**Adaptive assessment = separate computational intelligence.**

**Quantitative analysis = separate deterministic/statistical engine.**

**OpenAI never diagnoses, never changes measurements, and never controls the physical assessment.**

**API key stays on the backend.**

**Use structured outputs.**

**Send minimum necessary data.**

**If OpenAI fails, OralSense still works.**

Treat these requirements as persistent OralSense architecture context.
