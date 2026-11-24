# ORALSENSE — MASTER PRODUCT, ENGINEERING & UI/UX PROMPT

## 1. Your Role

Act as a senior full-stack engineer, product designer, UI/UX specialist, and software architect working on **OralSense**, a digital platform for structured oral somatosensory assessment.

Your responsibility is to inspect the existing repository, understand the current implementation, and turn it into a complete, coherent, reliable, polished application.

Do not immediately rewrite the project. First understand what already exists, what works, what is incomplete, and what needs improvement.

Work incrementally. Preserve useful existing code and functionality. Make practical engineering decisions without introducing unnecessary complexity.

**The goal is a full-featured, hackathon-ready application—not a reduced MVP and not an unnecessarily complicated enterprise platform.**

## 2. Product Overview

OralSense helps clinicians and researchers organize, conduct, record, analyze, and review oral somatosensory assessments.

Oral somatosensation includes sensory experiences such as oral touch, pressure, texture, temperature, and related sensations. These functions are relevant to research involving eating, chewing, swallowing, oral function, and sensory changes.

The platform should make assessment workflows more structured, records easier to manage, results easier to interpret, and data-quality issues easier to identify.

OralSense does not physically measure sensation by itself. Physical stimuli must be administered using appropriate procedures and equipment. The application records responses and processes observations according to the selected assessment method.

Do not present the platform as clinically validated, diagnostically accurate, or medically approved unless this is independently established.

## 3. First: Audit the Existing Repository

Before implementing anything:

1. Inspect the directory structure, package files, backend, frontend, database configuration, environment variables, and existing documentation.
2. Identify existing pages, components, routes, APIs, models, calculations, and incomplete functionality.
3. Determine which features already work and which are missing or broken.
4. Identify redundant dependencies, duplicated logic, and unnecessary architectural complexity.
5. Check whether the existing code contains hardcoded demo data, misleading metrics, insecure secrets, or simulated features presented as real.
6. Produce a concise implementation plan based on the actual repository.

Then implement the plan.

Do not delete working features simply to make the architecture look cleaner. Do not replace the entire application unless the current structure genuinely prevents progress.

## 4. Technology Stack

Use a simple, maintainable full-stack architecture.

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Recharts for charts and data visualizations
- Lucide icons for consistent interface icons

Use shadcn/ui components where useful, but do not turn the interface into a collection of generic component-library cards.

### Backend

- Python
- FastAPI
- Pydantic for request and response validation
- SQLAlchemy for database access
- Alembic for database migrations
- NumPy and SciPy only where scientifically or mathematically justified

### Database

- PostgreSQL

Use PostgreSQL as the application's actual persistent database. Do not substitute SQLite.

Design sensible relational models, foreign keys, constraints, indexes, and transactions. Use Alembic to manage schema changes.

Keep database access behind a clear, reusable data-access layer. Avoid unnecessarily abstract repository patterns or excessive layers.

### AI

- OpenAI API accessed exclusively through the FastAPI backend.
- Keep prompts, model configuration, response validation, and AI-related logic in dedicated backend modules.
- Treat AI as an optional supporting capability, not a dependency for ordinary application functionality.

Never expose API keys through frontend code, browser bundles, or `VITE_` environment variables.

### Avoid unnecessary technologies

Do not add:

- Kubernetes
- Microservices
- Redis without a demonstrated requirement
- A separate worker system without a demonstrated requirement
- GraphQL when ordinary REST endpoints are sufficient
- Multiple competing UI or chart libraries
- A complex cloud architecture
- A mandatory container orchestration setup
- A complicated CI/CD pipeline

Use a straightforward REST API and one application backend.

Do not introduce a new dependency when the existing stack can reasonably handle the task.

## 5. Full Product Scope

Preserve and implement the complete OralSense product, not just a few demonstration screens.

Organize the application around the following functional areas. Integrate them into the existing project structure where appropriate rather than blindly creating duplicate pages.

### A. Dashboard

Provide a useful overview of the user's assessment workspace.

Include:

- Recent assessments.
- Participant or research-record overview.
- Assessments in progress and completed assessments.
- Useful shortcuts to start or resume an assessment.
- Relevant activity and data-quality alerts.
- Meaningful summary visualizations when real data supports them.
- Clear empty states for new users.

Do not invent real patient counts, clinical outcomes, or performance improvements. Clearly label sample data.

### B. Participant and Research Record Management

Allow authorized users to create and manage participant records appropriate to the prototype's privacy requirements.

Include:

- Participant creation and editing.
- Stable internal identifiers.
- Relevant assessment metadata.
- Assessment history.
- Links between participants and their assessments.
- Sensible field validation.
- Duplicate and incomplete-record handling.
- Clear save, update, and failure feedback.

Minimize personally identifying information. Use synthetic participant records in the demonstration unless genuine data is explicitly authorized and appropriately protected.

Do not add a large account-management system unless the application actually requires it.

### C. Assessment Setup

Allow the user to prepare an assessment before recording observations.

Include:

- Participant selection.
- Assessment type and protocol selection where supported.
- Assessment metadata and session details.
- Trial configuration appropriate to the selected method.
- Instructions and relevant procedural information.
- Validation of required configuration.
- A clear summary before the assessment begins.

Assessment protocols must be represented honestly. Do not invent validated clinical procedures, normative ranges, or diagnostic thresholds.

Where a protocol is not fully established, label it as a configurable or demonstration protocol.

### D. Active Assessment Workspace

This is one of the most important parts of the product.

Create a focused, distraction-free workspace for the clinician or researcher conducting an assessment.

Include appropriate functionality for:

- Displaying the current trial and procedural instructions.
- Recording observations and participant responses.
- Moving between trials.
- Correcting an entry before finalization, with appropriate history or safeguards.
- Tracking progress.
- Validating required entries.
- Saving progress and resuming when appropriate.
- Handling interruptions, incomplete trials, and accidental navigation.
- Displaying clear confirmation when data is saved.

Keep physical stimulus administration under the control of the qualified person conducting the assessment.

Where the prototype simulates an assessment, explicitly label the simulation. Never suggest that the application has physically administered or measured a stimulus.

Make the workspace fast and easy to use with a mouse and keyboard. Avoid unnecessary modals, excessive clicks, and distracting animations.

### E. Assessment Results and Analysis

Provide an understandable view of recorded observations and any calculations justified by the selected protocol.

Potential capabilities include:

- Trial-level results.
- Summaries of recorded responses.
- Visualizations of response patterns.
- Comparisons between sessions when methodologically appropriate.
- Missing-data indicators.
- Data-quality flags.
- Uncertainty or threshold estimates only when the underlying method supports them.
- Exportable assessment records and results.

Separate raw observations from calculated values.

Make calculation assumptions, units, missing-data handling, and relevant protocol settings inspectable.

Never fabricate results to make a chart look complete. Do not imply that a chart or calculated score establishes a diagnosis.

### F. Assessment History and Longitudinal Review

Provide a useful way to find previous assessments and inspect changes over time.

Include:

- Search and filtering.
- Participant-specific assessment history.
- Session dates and status.
- Comparison of compatible assessments.
- Clear indication when two sessions cannot validly be compared.
- Access to prior observations and results.
- Appropriate handling of corrected or incomplete records.

Do not imply that observed changes are clinically significant unless the relevant method and evidence support that conclusion.

### G. AI-Assisted Quality Review

Build an AI feature that helps users inspect assessment records for possible quality issues.

Depending on the information available, it may:

- Identify missing or inconsistent entries.
- Flag unusual response patterns for human review.
- Summarize data-quality concerns.
- Highlight uncertainty or limitations.
- Suggest what the researcher should verify.
- Produce a concise, structured quality-review report.

The AI must not:

- Diagnose a participant.
- Prescribe treatment.
- Claim certainty unsupported by the data.
- Invent missing observations.
- Alter raw recorded data.
- Silently modify calculated results.
- Present its suggestions as validated clinical judgments.

AI review must be optional. The rest of the application must work when the API key is missing, the API request fails, or the service is unavailable.

Clearly distinguish AI-generated commentary from measured observations and deterministic calculations. Validate AI responses before displaying them.

Avoid sending personally identifying information to the AI service. Send only the minimum necessary, appropriately de-identified information.

### H. Export and Data Handling

Provide practical export functionality for assessment data and results.

Include:

- A useful CSV export for structured records.
- A readable report format where appropriate.
- Clear export status and error messages.
- Consistent units and field names.
- Appropriate handling of missing values.
- Protection against accidentally exposing unrelated participants' records.

Exports must accurately reflect stored information. Do not fabricate values or silently omit important limitations.

### I. Settings and Supporting Screens

Implement the supporting screens necessary to make the full application coherent, including relevant settings, protocol information, empty states, error states, and explanatory information.

Avoid creating pages that add no meaningful user value.

Navigation should remain consistent throughout the application.

## 6. Visual Identity and Color System

The visual identity should feel like a carefully designed scientific research product: modern, credible, calm, spacious, and technically sophisticated.

Avoid the generic appearance of a dashboard template assembled from dozens of cards.

Use this exact core palette.

### Primary palette

- **Deep Navy — `#102A43`**
  Primary navigation, strong headings, structural elements, and selected dark surfaces.
- **White — `#FFFFFF`**
  Main workspace background, clean surfaces, and visual breathing room.
- **Electric Lime — `#A3E635`**
  Primary calls to action, active progress, selected highlights, and important interactive accents.
- **Mist — `#EAF0F5`**
  Subtle secondary backgrounds, input surfaces where appropriate, section separation, and quiet panels.
- **Alert Red — `#EF4444`**
  Errors, failed operations, urgent data-quality attention, and destructive-action warnings.

### Supporting colors

Use restrained supporting neutrals:

- Muted slate for secondary text.
- Soft grey borders.
- Dark navy text on light surfaces.
- White text on sufficiently dark navy surfaces.

Use additional status colors only when they have clear meaning. Ensure warnings, success states, and informational messages remain distinguishable without relying solely on color.

### Color usage rules

1. White should dominate the main working area.
2. Navy should establish structure and hierarchy.
3. Lime should be an intentional accent, not a background color applied everywhere.
4. Red should communicate actual errors or attention, not decorate the interface.
5. Mist should separate content subtly rather than creating visually heavy boxes.
6. Maintain readable text contrast.
7. Do not place small white text on lime when contrast is insufficient.
8. Avoid unnecessary gradients, neon effects, and colorful card collections.
9. Use a consistent design-token system rather than scattered hardcoded color values.
10. Support clear hover, focus, selected, disabled, loading, success, warning, and error states.

## 7. UI/UX Direction: Spacious, Interactive, and Deliberate

UI/UX quality is a core product requirement, not a final cosmetic pass.

The application should feel custom-designed for OralSense rather than generated from a generic admin dashboard.

### Layout and spacing

- Use a consistent spacing scale.
- Give major sections generous breathing room.
- Establish a clear distinction between page title, explanatory text, controls, and content.
- Keep related information together.
- Avoid packing every possible metric into the first screen.
- Use readable line lengths and sensible maximum widths.
- Align page content, controls, and section headings consistently.
- Use responsive layouts that adapt naturally to different screen widths.
- Avoid horizontal scrolling except where a genuine data-table requirement makes it necessary.

Use a persistent, restrained sidebar on desktop where appropriate, with clear navigation labels and recognizable icons.

The main workspace should have a clear page heading, concise contextual information, and one obvious primary action.

Do not make the sidebar excessively wide or the content area unnecessarily narrow.

### Typography

Use a clean, modern sans-serif typeface such as Inter.

Create a consistent type scale for:

- Page titles.
- Section headings.
- Body text.
- Supporting descriptions.
- Form labels.
- Metadata.
- Numeric results.

Use font weight and spacing to establish hierarchy rather than making every heading large or bold.

Important results should be easy to scan, but scientific measurements must never be visually exaggerated beyond their meaning.

### Cards and surfaces

Use cards when they help group related information, not as the default container for everything.

Prefer:

- Open layouts.
- Subtle borders.
- Restrained corner radii.
- Light surface separation.
- Clear section boundaries.
- Carefully placed whitespace.

Avoid:

- Endless nested cards.
- Heavy drop shadows.
- Excessive pill-shaped elements.
- Large decorative empty areas.
- Unnecessary badges.
- Repeated containers inside containers.

### Interactive behavior

Every interactive element must have a clear purpose and a working behavior.

Implement:

- Immediate visual feedback on selection.
- Smooth but restrained hover and focus states.
- Useful transitions between related views.
- Clear loading states for operations that take time.
- Inline validation near the relevant fields.
- Confirmation for genuinely destructive actions.
- Undo or correction flows where practical.
- Helpful empty states that tell the user what to do next.
- Tooltips only when an icon or control is not self-explanatory.
- Keyboard navigation and visible focus indicators.
- Accessible form labels and understandable error messages.

Use animation to communicate state changes, progress, or navigation—not to decorate every element.

Prefer short transitions that do not delay the user. Respect reduced-motion preferences.

Do not use animations that interfere with clinical or research workflows.

### Forms and data entry

Forms should feel calm and predictable.

- Group fields into logical sections.
- Use clear labels rather than placeholder-only instructions.
- Explain unusual fields briefly.
- Mark required fields.
- Validate input without making the form frustrating.
- Preserve valid user input when a submission fails.
- Prevent accidental duplicate submissions.
- Show save status.
- Avoid presenting every possible setting at once when progressive disclosure is more appropriate.

### Charts and scientific visualizations

Use Recharts for useful, interactive visualizations.

Charts should:

- Have descriptive titles.
- Label axes and units.
- Use sensible scales.
- Show tooltips for relevant data points.
- Provide clear legends when multiple series are present.
- Distinguish missing data from zero values.
- Support empty and insufficient-data states.
- Remain readable at different viewport sizes.
- Use the palette consistently.
- Avoid unnecessary 3D effects and decorative chart elements.

Where appropriate, allow the user to change filters, time ranges, sessions, or series and see the visualization update.

Do not create interactive chart controls that have no effect.

Include an accessible text or tabular alternative for important results.

### Active assessment screen

Give this screen its own carefully considered layout.

It should prioritize:

1. Participant or assessment identifier.
2. Current procedure and trial.
3. Response-entry controls.
4. Trial progress.
5. Save status.
6. Clear next/back actions.
7. Relevant protocol guidance.

Minimize unrelated navigation and visual noise while an assessment is active.

Use navy for structure, white for the workspace, mist for secondary regions, and lime for the main progression action.

Reserve red for genuine problems or critical warnings.

### Responsive behavior

Desktop is the primary environment, but the application should still work on tablet and smaller screens.

At smaller widths:

- Collapse the sidebar into a usable navigation pattern.
- Stack content logically.
- Keep important controls accessible.
- Prevent tables and forms from breaking the layout.
- Preserve the hierarchy of the active assessment workspace.

Do not merely shrink the desktop interface.

### Reference quality

Aim for the finish of a strong modern research SaaS product: deliberate spacing, a coherent visual system, clear interactions, and purposeful data presentation.

The Race Pakistan website may be used as inspiration for confidence, identity, and motion. Do not copy its branding, layout, or assets. OralSense must maintain its own scientific and research-oriented identity.

## 8. Frontend Architecture

Keep the frontend organized by product feature.

Use a sensible structure for:

- Application shell and navigation.
- Reusable UI components.
- Feature-specific pages and components.
- API client and typed API responses.
- Form validation.
- Charts and visualizations.
- Shared TypeScript types.
- Loading, error, and empty states.

Separate business logic from visual components where that improves clarity.

Avoid:

- One enormous component containing the whole application.
- Copy-pasted components for similar features.
- Global state libraries without a real need.
- Giant context providers holding unrelated state.
- Duplicated API calls and inconsistent error handling.
- Overengineering every simple component.

Use local component state for local interactions. Introduce shared state only when multiple parts of the application genuinely need it.

Keep TypeScript useful. Avoid `any` unless there is a clearly justified exception.

## 9. Backend Architecture

Keep the backend modular but straightforward.

Organize code into understandable areas for:

- API routes.
- Configuration.
- Database connection and sessions.
- Database models.
- Request and response schemas.
- Business logic.
- Scientific calculations.
- AI quality review.
- Export functionality.
- Error handling.

Use Pydantic validation at API boundaries.

Use SQLAlchemy and PostgreSQL consistently. Use Alembic migrations rather than relying on automatic table creation in application startup.

Keep calculation logic independently testable and avoid mixing scientific calculations into route handlers.

Use transactions where multiple database changes must succeed or fail together.

Add sensible pagination, filtering, and indexes where the data volume or access pattern justifies them.

Do not build an elaborate generic framework inside the application.

## 10. Scientific Integrity and Data Quality

Scientific correctness matters more than visual impressiveness.

Maintain a clear distinction between:

- Raw observations entered by a human.
- Derived values calculated by deterministic application logic.
- Interpretation or commentary produced by AI.
- Synthetic demonstration data.

For every implemented calculation, document the relevant method, inputs, units, assumptions, and limitations.

Use appropriate numerical validation and handle missing, malformed, or insufficient data explicitly.

Never silently replace missing values with zero.

Do not apply statistical or signal-processing methods simply to make the application look sophisticated.

Only implement threshold estimation, adaptive trial selection, normative comparisons, or uncertainty calculations when the method is appropriate and sufficiently specified. If a feature is demonstrative rather than validated, identify it as such.

Where calculations are not justified by the available protocol, show the recorded observations and state the limitation instead of inventing an algorithm.

Preserve raw records when corrections are made. Where relevant, retain timestamps and a traceable record of meaningful changes.

## 11. Security and Privacy

Implement security proportionate to the application and its actual users.

- Keep secrets in environment variables.
- Include an `.env.example` containing placeholders only.
- Ignore real `.env` files in Git.
- Never put server API keys in frontend environment variables or browser code.
- Validate and constrain user input.
- Use parameterized database operations through SQLAlchemy.
- Configure CORS for the actual frontend origin rather than allowing every origin by default.
- Avoid exposing stack traces and secrets in production-facing API errors.
- Avoid logging sensitive participant information.
- Avoid sending identifiable participant data to the AI API.
- Ensure record queries respect the application's intended access boundaries.
- Do not pretend simulated authentication provides real security.
- Avoid storing unnecessary personal or medical information.

If authentication is needed, choose the simplest defensible implementation that fits the product. Do not introduce a complex identity provider unless a genuine requirement justifies it.

## 12. Testing: Focused and Practical

Do not create an enormous testing program.

Use a small, useful testing setup that catches important regressions.

Prioritize:

- Core calculation and validation tests.
- Backend API tests for critical workflows.
- Database persistence and relationship tests.
- Tests for invalid or incomplete assessment data.
- Tests ensuring AI failure does not break the application.
- A focused end-to-end walkthrough of the primary user journey.

Test realistic edge cases, including missing fields, malformed values, failed requests, and empty datasets.

Do not spend excessive time testing every decorative UI detail.

Use existing test tools if they are already appropriate. Otherwise, introduce the minimum needed, such as pytest for the backend and a suitable frontend test setup if important UI logic warrants it.

Keep the main user journey manually verifiable.

## 13. Deployment: Keep It Simple

The project must be straightforward to run locally and demonstrate.

Provide:

- Clear setup instructions.
- A documented PostgreSQL configuration.
- An `.env.example`.
- Database migration commands.
- Frontend development commands.
- Backend development commands.
- Instructions for running the application.
- A clear explanation of the AI API key requirement.
- A practical deployment guide appropriate to the chosen hosting environment.

Prefer a simple deployment path using a managed PostgreSQL instance and straightforward frontend/backend hosting, where suitable.

Do not require Kubernetes, multi-service orchestration, complicated infrastructure-as-code, or a large cloud setup.

Docker is optional, not mandatory. Add it only if it materially simplifies setup or deployment for this repository.

Do not configure CI/CD. It is unnecessary for this project unless a platform or existing repository setup makes a minimal configuration genuinely useful and Cursor can implement and verify it without distracting from product work. Never spend substantial time on pipelines.

Do not claim deployment is successful unless it has actually been performed and verified. Clearly distinguish local development from a deployed public application.

## 14. Performance and Reliability

Keep the application responsive and predictable.

- Avoid unnecessary network requests.
- Avoid repeated expensive calculations.
- Use loading indicators for asynchronous operations.
- Handle timeouts and failed requests.
- Prevent accidental duplicate submissions.
- Keep lists and charts efficient for expected data sizes.
- Avoid needless frontend dependencies.
- Avoid unnecessary database queries and repeated relationship loading.
- Make errors actionable and understandable.

Do not introduce complex caching, queues, or optimization infrastructure without evidence that it is needed.

## 15. AI Implementation Requirements

Build AI features so they remain optional and maintainable.

- Use the backend to call the OpenAI API.
- Read the API key from server-side configuration.
- Keep prompts in dedicated files or modules.
- Send only necessary, de-identified assessment information.
- Validate the returned structure before displaying it.
- Treat AI output as untrusted content.
- Clearly label AI-generated findings.
- Never allow AI output to overwrite raw observations or authoritative calculated values.
- Handle missing keys, rate limits, timeouts, malformed responses, and service failures gracefully.
- Provide a useful fallback when AI is unavailable.

Do not call the AI API for deterministic calculations that ordinary code can perform reliably.

Do not use AI-generated numbers as if they were measured or scientifically calculated results.

## 16. Error States and Edge Cases

Implement the error handling the actual product needs.

Cover:

- Failed API requests.
- Database connection failures.
- Invalid form submissions.
- Duplicate or conflicting records.
- Missing required assessment data.
- Incomplete trials.
- Unsaved changes.
- Invalid protocol configuration.
- Empty search results.
- Empty charts and insufficient data.
- Failed exports.
- AI service failures.
- Invalid or expired application state where applicable.

Show understandable messages and offer a recovery action when possible.

Avoid silently swallowing errors or showing raw internal exceptions to users.

## 17. Documentation and Project Quality

Keep documentation useful rather than enormous.

Update the README with:

- What OralSense does.
- The actual implemented features.
- Technology stack.
- Project structure.
- Local setup.
- PostgreSQL setup.
- Environment configuration.
- Database migration instructions.
- How to run frontend and backend.
- How to enable AI features.
- How to use the core workflow.
- Testing instructions.
- Known limitations.
- Clear disclosure of simulated features and synthetic data.

Add concise documentation for scientific calculations and assessment protocols where needed.

Do not claim features exist if they are only planned or mocked.

Do not include real secrets, personal participant information, or confidential research records in the repository.

## 18. Git Discipline and Authorship

The project author is **Muhammad Hassan Jamshaid**.

Do not add Cursor or an AI tool as a project co-author or replace the project's authorship information.

Before making Git changes:

- Inspect `git status`.
- Review relevant diffs.
- Preserve unrelated user changes.
- Never overwrite uncommitted work without permission.
- Do not push, publish, or change repository settings without authorization.
- Do not change Git identity without permission.
- Never commit API keys, `.env` files, private data, or generated secrets.

Do not automatically commit every change.

## 19. Implementation Workflow

Follow this order:

### Phase 1 — Audit

Inspect the repository and identify the actual implementation state.

### Phase 2 — Plan

Create a concise checklist of the required product functionality, architectural corrections, UI/UX improvements, and major risks.

### Phase 3 — Foundation

Stabilize the application structure, environment configuration, database connection, migrations, API conventions, and design tokens.

Do not rebuild working infrastructure without a reason.

### Phase 4 — Product Functionality

Implement the full user journey, including participant records, assessment setup, active assessment, persistence, analysis, history, export, and AI quality review.

Keep frontend and backend contracts consistent.

### Phase 5 — UI/UX

Polish every implemented screen using the OralSense visual system. Check spacing, hierarchy, interactions, responsive behavior, accessibility, loading states, and error states.

Do not leave UI polish until the last moment.

### Phase 6 — Verification

Run the relevant available checks. Verify database migrations and critical endpoints. Test the core workflow from beginning to end.

Fix the important failures before adding secondary features.

### Phase 7 — Documentation

Update the README and document any remaining limitations.

After each substantial phase, summarize:

- What changed.
- What works.
- What was tested.
- What remains incomplete.
- Any setup steps I need to perform manually.

## 20. Definition of Done

OralSense is ready for its hackathon demonstration when:

1. The full intended product workflow is implemented to a coherent, demonstrable standard.
2. The frontend communicates correctly with the FastAPI backend.
3. Assessment and participant records persist in PostgreSQL.
4. The main assessment workflow handles valid, incomplete, and invalid inputs appropriately.
5. Results are traceable to recorded data and documented calculations.
6. History and exports work for implemented data types.
7. AI quality review works when configured and fails gracefully when unavailable.
8. Synthetic data and simulated procedures are explicitly identified.
9. The interface feels polished, spacious, consistent, and genuinely interactive.
10. The application can be run using the documented setup instructions.
11. Critical tests and the main end-to-end walkthrough pass.
12. The README accurately describes the actual implementation and its scientific limitations.

Do not mark a feature complete merely because its screen exists. Its meaningful interactions, data handling, and error states must work.

## Final Instruction

Start by auditing the existing repository.

Then give me a concise summary of the current state and a prioritized implementation plan. After that, implement the plan incrementally, preserving working code.

**Build the complete OralSense product with strong scientific integrity and excellent UI/UX. Simplify the stack, testing, and deployment—not the product.**

Choose sensible defaults instead of repeatedly asking me to make routine engineering decisions. If a decision materially affects scientific validity, privacy, cost, or an irreversible action, explain the trade-off before proceeding.

Do not stop after producing a plan. Continue implementing, testing, and improving the actual code within the available environment. Clearly state anything that genuinely requires my credentials, approval, or manual action.
