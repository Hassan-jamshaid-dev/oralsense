import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/buttonClasses";
import { Select, TextArea, TextField } from "../../components/ui/Field";
import { ApiError, updateWorkspace } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { isResearchRole, RESEARCH_ROLE_OPTIONS } from "../../lib/roles";
import type { Me, ResearchRole, UpdateWorkspaceRequest, Workspace } from "../../lib/types";
import { activeContext, formatContext } from "../../lib/workflow";
import { useAuth } from "../auth/authContext";
import {
  characterCount,
  DESCRIPTION_MAX,
  hasErrors,
  pickWorkspaceFieldErrors,
  validateDescription,
  validateDisplayName,
  validateWorkspaceName,
} from "./validation";
import type { WorkspaceFieldErrors } from "./validation";

type FormValues = {
  workspaceName: string;
  description: string;
  displayName: string;
  researchRole: ResearchRole | "";
};

function valuesFromMe(me: Me, workspace: Workspace): FormValues {
  return {
    workspaceName: workspace.name,
    description: workspace.description ?? "",
    displayName: me.user.display_name ?? "",
    researchRole: me.membership?.research_role ?? "",
  };
}

function buildChanges(values: FormValues, saved: FormValues, canEditWorkspace: boolean): UpdateWorkspaceRequest {
  const changes: UpdateWorkspaceRequest = {};
  if (canEditWorkspace) {
    const name = values.workspaceName.trim();
    if (name !== saved.workspaceName) changes.workspace_name = name;
    const description = values.description.trim();
    if (description !== saved.description) changes.description = description || null;
  }
  const displayName = values.displayName.trim();
  if (displayName !== saved.displayName) changes.display_name = displayName;
  if (values.researchRole !== saved.researchRole) changes.research_role = values.researchRole || null;
  return changes;
}

export function EditWorkspaceForm({ me, workspace }: { me: Me; workspace: Workspace }) {
  const { setMe, expireSession } = useAuth();
  const canEditWorkspace = me.membership?.access_role === "owner";
  const saved = valuesFromMe(me, workspace);

  const [values, setValues] = useState<FormValues>(saved);
  const [errors, setErrors] = useState<WorkspaceFieldErrors>({});
  const [serverError, setServerError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const pendingRef = useRef(false);
  const workspaceNameRef = useRef<HTMLInputElement>(null);
  const descriptionRef = useRef<HTMLTextAreaElement>(null);
  const displayNameRef = useRef<HTMLInputElement>(null);

  const changes = buildChanges(values, saved, canEditWorkspace);
  const dirty = Object.keys(changes).length > 0;

  function updateValue<K extends keyof FormValues>(key: K, value: FormValues[K], errorKey: keyof WorkspaceFieldErrors) {
    setValues((current) => ({ ...current, [key]: value }));
    setJustSaved(false);
    if (errors[errorKey]) setErrors((current) => ({ ...current, [errorKey]: undefined }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pendingRef.current || !dirty) return;

    const clientErrors: WorkspaceFieldErrors = {
      workspace_name: canEditWorkspace ? validateWorkspaceName(values.workspaceName) : undefined,
      description: canEditWorkspace ? validateDescription(values.description) : undefined,
      display_name: validateDisplayName(values.displayName),
    };
    setErrors(clientErrors);
    setServerError(null);
    if (clientErrors.workspace_name) return workspaceNameRef.current?.focus();
    if (clientErrors.description) return descriptionRef.current?.focus();
    if (clientErrors.display_name) return displayNameRef.current?.focus();

    pendingRef.current = true;
    setPending(true);
    try {
      const updated = await updateWorkspace(changes);
      setMe(updated);
      if (updated.workspace) setValues(valuesFromMe(updated, updated.workspace));
      setJustSaved(true);
    } catch (error) {
      setJustSaved(false);
      if (isUnauthorized(error)) return expireSession();
      setErrors(pickWorkspaceFieldErrors(error instanceof ApiError ? error.fields : null));
      setServerError(error instanceof ApiError ? error : new ApiError(0, "unknown_error", getErrorMessage(error)));
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  const fieldErrorsShown = hasErrors(errors);

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-navy sm:text-3xl">Workspace details</h1>
      <p className="mt-2 text-sm text-slate">Update how your workspace and your profile appear to your team.</p>
      <p className="mt-4 text-sm text-slate">
        Working context: <span className="font-medium text-navy">{formatContext(activeContext(me.membership))}</span>.
        Switch it from the sidebar. Records stay in the context where they were created.
      </p>

      <div className="mt-8 flex flex-col gap-3 empty:hidden">
        {justSaved ? (
          <Alert variant="success" title="Saved">
            Your workspace details were saved.
          </Alert>
        ) : null}
        {serverError ? (
          <Alert variant="error" title="Changes weren't saved">
            {serverError.code === "validation_error" && !fieldErrorsShown
              ? serverError.message
              : getErrorMessage(serverError)}
          </Alert>
        ) : null}
      </div>

      <form noValidate onSubmit={handleSubmit} className="mt-8 rounded-lg border border-border">
        <fieldset className="flex flex-col gap-6 p-6 sm:p-8">
          <legend className="float-left mb-2 w-full text-base font-semibold text-navy">Workspace</legend>
          {canEditWorkspace ? null : (
            <p className="text-sm text-slate">Only the workspace owner can change the name and description.</p>
          )}
          <TextField
            ref={workspaceNameRef}
            label="Workspace name"
            required
            readOnly={!canEditWorkspace}
            value={values.workspaceName}
            error={errors.workspace_name}
            onChange={(event) => updateValue("workspaceName", event.target.value, "workspace_name")}
          />
          <TextArea
            ref={descriptionRef}
            label="Description"
            readOnly={!canEditWorkspace}
            value={values.description}
            error={errors.description}
            meta={canEditWorkspace ? `${characterCount(values.description)}/${DESCRIPTION_MAX}` : undefined}
            onChange={(event) => updateValue("description", event.target.value, "description")}
          />
        </fieldset>

        <fieldset className="flex flex-col gap-6 border-t border-border p-6 sm:p-8">
          <legend className="float-left mb-2 w-full text-base font-semibold text-navy">About you</legend>
          <TextField
            ref={displayNameRef}
            label="Display name"
            required
            autoComplete="name"
            value={values.displayName}
            error={errors.display_name}
            hint="Shown to other members of this workspace."
            onChange={(event) => updateValue("displayName", event.target.value, "display_name")}
          />
          <Select
            label="Team role"
            value={values.researchRole}
            error={errors.research_role}
            hint="Optional. It describes your role and doesn't change your permissions."
            onChange={(event) => {
              const value = event.target.value;
              updateValue("researchRole", isResearchRole(value) ? value : "", "research_role");
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

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border px-6 py-4 sm:px-8">
          <p
            role="status"
            className={`mr-auto text-sm ${serverError ? "text-red-text" : "text-slate"}`}
          >
            {pending ? "Saving…" : serverError ? "Save failed" : dirty ? "Unsaved changes" : justSaved ? "Saved" : "No changes"}
          </p>
          <Link to="/app" className={buttonClasses({ variant: "secondary" })}>
            Cancel
          </Link>
          <Button type="submit" loading={pending} disabled={!dirty}>
            {pending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </div>
  );
}
