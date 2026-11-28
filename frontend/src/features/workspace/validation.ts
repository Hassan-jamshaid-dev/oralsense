// Client-side checks mirror the backend limits for faster feedback; the backend
// remains the authority and its field errors are mapped back onto these fields.

export type WorkspaceFieldName = "workspace_name" | "description" | "display_name" | "research_role" | "context";
export type WorkspaceFieldErrors = Partial<Record<WorkspaceFieldName, string>>;

export const WORKSPACE_NAME_MIN = 2;
export const WORKSPACE_NAME_MAX = 120;
export const DESCRIPTION_MAX = 500;
export const DISPLAY_NAME_MAX = 80;

const FIELD_NAMES: ReadonlyArray<WorkspaceFieldName> = [
  "workspace_name",
  "description",
  "display_name",
  "research_role",
  "context",
];

/** Counts characters the way the backend does (code points, not UTF-16 units). */
export function characterCount(value: string): number {
  return [...value].length;
}

export function validateWorkspaceName(value: string): string | undefined {
  const length = characterCount(value.trim());
  if (length === 0) return "Enter a workspace name.";
  if (length < WORKSPACE_NAME_MIN) return `Use at least ${WORKSPACE_NAME_MIN} characters.`;
  if (length > WORKSPACE_NAME_MAX) return `Use ${WORKSPACE_NAME_MAX} characters or fewer.`;
  return undefined;
}

export function validateDescription(value: string): string | undefined {
  if (characterCount(value.trim()) > DESCRIPTION_MAX) return `Use ${DESCRIPTION_MAX} characters or fewer.`;
  return undefined;
}

export function validateDisplayName(value: string): string | undefined {
  const length = characterCount(value.trim());
  if (length === 0) return "Enter the name your team will see.";
  if (length > DISPLAY_NAME_MAX) return `Use ${DISPLAY_NAME_MAX} characters or fewer.`;
  return undefined;
}

export function validateContext(value: string): string | undefined {
  if (value !== "clinical" && value !== "research") return "Choose clinical or research.";
  return undefined;
}

export function pickWorkspaceFieldErrors(fields: Record<string, string> | null): WorkspaceFieldErrors {
  const errors: WorkspaceFieldErrors = {};
  if (fields === null) return errors;
  for (const name of FIELD_NAMES) {
    if (fields[name]) errors[name] = fields[name];
  }
  return errors;
}

export function hasErrors(errors: WorkspaceFieldErrors): boolean {
  return Object.values(errors).some(Boolean);
}
