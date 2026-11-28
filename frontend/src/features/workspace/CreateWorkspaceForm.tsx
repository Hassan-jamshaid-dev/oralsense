import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, Check, CircleCheck, RotateCw } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/buttonClasses";
import { Select, TextArea, TextField } from "../../components/ui/Field";
import { ApiError, createWorkspace } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { isResearchRole, RESEARCH_ROLE_OPTIONS } from "../../lib/roles";
import type { Me, ResearchRole, WorkflowContext } from "../../lib/types";
import { useAuth } from "../auth/authContext";
import {
  characterCount,
  DESCRIPTION_MAX,
  hasErrors,
  pickWorkspaceFieldErrors,
  validateContext,
  validateDescription,
  validateDisplayName,
  validateWorkspaceName,
} from "./validation";
import type { WorkspaceFieldErrors } from "./validation";

type Step = 1 | 2;
const STEPS: ReadonlyArray<{ step: Step; label: string }> = [
  { step: 1, label: "Workspace" },
  { step: 2, label: "About you" },
];
const REDIRECT_DELAY_MS = 1200;

const CONTEXT_OPTIONS: ReadonlyArray<{ value: WorkflowContext; title: string; body: string }> = [
  {
    value: "clinical",
    title: "Clinical",
    body: "Patients and clinical assessment history. You remain responsible for any diagnosis.",
  },
  {
    value: "research",
    title: "Research",
    body: "Participants and research records. A participant code is assigned when you add someone.",
  },
];

function StepIndicator({ current }: { current: Step }) {
  return (
    <ol aria-label="Setup progress" className="flex items-center gap-3">
      {STEPS.map(({ step, label }, index) => {
        const done = step < current;
        const active = step === current;
        return (
          <li key={step} aria-current={active ? "step" : undefined} className="flex items-center gap-3">
            {index > 0 ? <span aria-hidden="true" className="h-px w-8 bg-border" /> : null}
            <span
              aria-hidden="true"
              className={`flex size-7 items-center justify-center rounded-full text-xs font-semibold tabular-nums ${
                active ? "bg-lime text-navy" : done ? "bg-navy text-white" : "border border-border text-slate"
              }`}
            >
              {done ? <Check size={14} /> : step}
            </span>
            <span className={`text-sm ${active ? "font-semibold text-navy" : "text-slate"}`}>
              <span className="sr-only">
                Step {step} of {STEPS.length}:{" "}
              </span>
              {label}
              {done ? <span className="sr-only"> (completed)</span> : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function CreateWorkspaceForm({ me }: { me: Me }) {
  const { setMe, refreshMe, expireSession } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>(1);
  const [workspaceName, setWorkspaceName] = useState("");
  const [description, setDescription] = useState("");
  const [displayName, setDisplayName] = useState(me.user.display_name ?? "");
  const [researchRole, setResearchRole] = useState<ResearchRole | "">("");
  const [context, setContext] = useState<WorkflowContext | "">("");
  const [errors, setErrors] = useState<WorkspaceFieldErrors>({});
  const [serverError, setServerError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const [created, setCreated] = useState(false);
  const pendingRef = useRef(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const workspaceNameRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const displayNameRef = useRef<HTMLInputElement>(null);
  const movedStep = useRef(false);

  useEffect(() => {
    if (movedStep.current) headingRef.current?.focus();
  }, [step]);

  useEffect(() => {
    if (!created) return;
    headingRef.current?.focus();
    const timer = window.setTimeout(() => navigate("/app", { replace: true }), REDIRECT_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [created, navigate]);

  function goToStep(next: Step) {
    movedStep.current = true;
    setStep(next);
  }

  function clearFieldError(field: keyof WorkspaceFieldErrors) {
    if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }));
  }

  function continueToDetails() {
    const stepErrors: WorkspaceFieldErrors = {
      workspace_name: validateWorkspaceName(workspaceName),
      description: validateDescription(description),
      context: validateContext(context),
    };
    setErrors((current) => ({ ...current, ...stepErrors }));
    if (stepErrors.workspace_name) return workspaceNameRef.current?.focus();
    if (stepErrors.description) return descriptionRef.current?.focus();
    if (stepErrors.context) return document.getElementById("workspace-context-clinical")?.focus();
    goToStep(2);
  }

  async function submitWorkspace() {
    if (pendingRef.current) return;
    const allErrors: WorkspaceFieldErrors = {
      workspace_name: validateWorkspaceName(workspaceName),
      description: validateDescription(description),
      display_name: validateDisplayName(displayName),
      context: validateContext(context),
    };
    setErrors(allErrors);
    setServerError(null);
    if (allErrors.workspace_name || allErrors.description || allErrors.context) return goToStep(1);
    if (allErrors.display_name) return displayNameRef.current?.focus();
    if (context !== "clinical" && context !== "research") return goToStep(1);

    pendingRef.current = true;
    setPending(true);
    try {
      const updated = await createWorkspace({
        workspace_name: workspaceName.trim(),
        description: description.trim() || null,
        display_name: displayName.trim(),
        research_role: researchRole || null,
        context,
      });
      setMe(updated);
      setCreated(true);
    } catch (error) {
      if (isUnauthorized(error)) return expireSession();
      if (error instanceof ApiError && error.code === "workspace_exists") {
        await refreshMe();
        navigate("/app", { replace: true });
        return;
      }
      const fieldErrors = pickWorkspaceFieldErrors(error instanceof ApiError ? error.fields : null);
      setErrors(fieldErrors);
      if (fieldErrors.workspace_name || fieldErrors.description || fieldErrors.context) goToStep(1);
      setServerError(error instanceof ApiError ? error : new ApiError(0, "unknown_error", getErrorMessage(error)));
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (step === 1) continueToDetails();
    else void submitWorkspace();
  }

  if (created) {
    return (
      <div className="animate-fade-in rounded-lg border border-border p-8">
        <span className="flex size-10 items-center justify-center rounded-full bg-lime text-navy">
          <CircleCheck size={22} aria-hidden="true" />
        </span>
        <h1 ref={headingRef} tabIndex={-1} className="outline-none mt-5 text-2xl font-semibold tracking-tight text-navy">
          Workspace created
        </h1>
        <p className="mt-2 text-sm text-slate">Opening your dashboard…</p>
        <Link to="/app" replace className={buttonClasses({ className: "mt-6" })}>
          Continue to dashboard
        </Link>
      </div>
    );
  }

  const fieldErrorsShown = hasErrors(errors);
  const descriptionLength = characterCount(description);

  return (
    <div>
      <p className="text-sm font-medium text-slate">Workspace setup</p>
      <h1 ref={headingRef} tabIndex={-1} className="outline-none mt-1 text-2xl font-semibold tracking-tight text-navy sm:text-3xl">
        {step === 1 ? "Set up your workspace" : "Tell your team who you are"}
      </h1>
      <p className="mt-2 text-sm text-slate">
        {step === 1
          ? "Choose clinical or research work for this workspace. You can switch later. Records stay in the context where they were created."
          : "This is how you appear to other members of the workspace."}
      </p>

      <div className="mt-8">
        <StepIndicator current={step} />
      </div>

      {serverError ? (
        <Alert
          variant="error"
          title="Couldn't create the workspace"
          className="mt-8"
          action={
            fieldErrorsShown ? undefined : (
              <Button variant="secondary" size="sm" onClick={() => void submitWorkspace()} loading={pending}>
                {pending ? null : <RotateCw size={14} aria-hidden="true" />}
                Retry
              </Button>
            )
          }
        >
          {serverError.code === "validation_error" && !fieldErrorsShown
            ? serverError.message
            : getErrorMessage(serverError)}
        </Alert>
      ) : null}

      <form noValidate onSubmit={handleSubmit} className="mt-8 rounded-lg border border-border p-6 sm:p-8">
        {step === 1 ? (
          <fieldset key="workspace" className="flex animate-fade-in flex-col gap-6">
            <legend className="sr-only">Workspace</legend>
            <TextField
              ref={workspaceNameRef}
              label="Workspace name"
              required
              autoComplete="organization"
              value={workspaceName}
              error={errors.workspace_name}
              hint="For example, the name of your lab or research group."
              onChange={(event) => {
                setWorkspaceName(event.target.value);
                clearFieldError("workspace_name");
              }}
            />
            <TextArea
              ref={descriptionRef}
              label="Description"
              value={description}
              error={errors.description}
              hint="What this workspace is for. You can change it later."
              meta={`${descriptionLength}/${DESCRIPTION_MAX}`}
              onChange={(event) => {
                setDescription(event.target.value);
                clearFieldError("description");
              }}
            />
            <fieldset className="flex flex-col gap-3">
              <legend className="text-sm font-medium text-navy">
                Working context
                <span className="ml-2 text-xs font-normal text-slate">Required</span>
              </legend>
              {CONTEXT_OPTIONS.map((option) => {
                const selected = context === option.value;
                return (
                  <label
                    key={option.value}
                    className={`flex cursor-pointer gap-3 rounded-md border px-4 py-3 ${
                      selected ? "border-navy bg-white" : "border-border bg-white"
                    }`}
                  >
                    <input
                      id={option.value === "clinical" ? "workspace-context-clinical" : "workspace-context-research"}
                      type="radio"
                      name="context"
                      value={option.value}
                      checked={selected}
                      className="mt-1"
                      onChange={() => {
                        setContext(option.value);
                        clearFieldError("context");
                      }}
                    />
                    <span>
                      <span className="block text-sm font-medium text-navy">{option.title}</span>
                      <span className="mt-1 block text-sm text-slate">{option.body}</span>
                    </span>
                  </label>
                );
              })}
              {errors.context ? <p className="text-sm text-red-text">{errors.context}</p> : null}
            </fieldset>
          </fieldset>
        ) : (
          <fieldset key="about" className="flex animate-fade-in flex-col gap-6">
            <legend className="sr-only">About you</legend>
            <TextField
              ref={displayNameRef}
              label="Display name"
              required
              autoComplete="name"
              value={displayName}
              error={errors.display_name}
              hint="Shown to other members of this workspace."
              onChange={(event) => {
                setDisplayName(event.target.value);
                clearFieldError("display_name");
              }}
            />
            <Select
              label="Team role"
              value={researchRole}
              error={errors.research_role}
              hint="Optional. It describes your role and doesn't change your permissions."
              onChange={(event) => {
                const value = event.target.value;
                setResearchRole(isResearchRole(value) ? value : "");
                clearFieldError("research_role");
              }}
            >
              <option value="">Not specified</option>
              {RESEARCH_ROLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </fieldset>
        )}

        <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6">
          {step === 2 ? (
            <Button variant="ghost" onClick={() => goToStep(1)} disabled={pending}>
              <ArrowLeft size={16} aria-hidden="true" />
              Back
            </Button>
          ) : (
            <span />
          )}
          <Button type="submit" loading={pending}>
            {step === 1 ? "Continue" : pending ? "Creating workspace…" : "Create workspace"}
          </Button>
        </div>
      </form>
    </div>
  );
}
