import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router";
import { ArrowLeft, RotateCw } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/buttonClasses";
import { TextField } from "../../components/ui/Field";
import { ApiError, createParticipant } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { useDocumentTitle } from "../../lib/useDocumentTitle";
import { activeContext, WORKFLOW_WORDS } from "../../lib/workflow";
import { useAuth } from "../auth/authContext";

const LABEL_MAX = 80;

type FieldErrors = { display_label?: string };

/** Code points, so the counter matches the length the API enforces after trim. */
function characterCount(value: string): number {
  return [...value].length;
}

function validateDisplayLabel(value: string, required: boolean): string | undefined {
  const length = characterCount(value.trim());
  if (required && length === 0) return "Enter a name or label.";
  if (length > LABEL_MAX) return `Use ${LABEL_MAX} characters or fewer.`;
  return undefined;
}

function hasErrors(errors: FieldErrors): boolean {
  return Object.values(errors).some(Boolean);
}

function serverFieldErrors(error: ApiError): FieldErrors {
  const errors: FieldErrors = {};
  if (error.fields?.display_label) errors.display_label = error.fields.display_label;
  return errors;
}

function alertMessage(error: ApiError, fieldErrors: FieldErrors): string {
  // Duplicate conflicts must show the API sentence, not a rewritten client string.
  if (error.status === 409) return error.message;
  if (error.code === "validation_error" && !hasErrors(fieldErrors)) return error.message;
  return getErrorMessage(error);
}

export function AddParticipantPage() {
  const navigate = useNavigate();
  const { me, expireSession } = useAuth();
  const words = WORKFLOW_WORDS[activeContext(me?.membership)];
  const labelRequired = activeContext(me?.membership) === "clinical";
  useDocumentTitle(words.addTitle);

  const [displayLabel, setDisplayLabel] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [serverError, setServerError] = useState<ApiError | null>(null);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);
  const labelRef = useRef<HTMLInputElement>(null);
  const alertRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    labelRef.current?.focus();
  }, []);

  function clearField() {
    if (errors.display_label) setErrors({});
    if (serverError) setServerError(null);
  }

  async function submitParticipant() {
    if (pendingRef.current) return;

    const nextErrors: FieldErrors = {
      display_label: validateDisplayLabel(displayLabel, labelRequired),
    };
    setErrors(nextErrors);
    setServerError(null);
    if (nextErrors.display_label) return labelRef.current?.focus();

    // Held for the whole request so a second submit cannot start before React re-renders.
    pendingRef.current = true;
    setPending(true);
    try {
      const created = await createParticipant({
        display_label: displayLabel.trim() || null,
      });
      // The client resolves only for an OK response. This route returns 201.
      if (created.id.length === 0) {
        setServerError(new ApiError(0, "internal_error", "The server returned an unexpected response."));
        pendingRef.current = false;
        setPending(false);
        return;
      }
      navigate(`/app/participants/${created.id}`);
    } catch (error) {
      pendingRef.current = false;
      setPending(false);
      if (isUnauthorized(error)) return expireSession();
      const apiError = error instanceof ApiError ? error : new ApiError(0, "unknown_error", getErrorMessage(error));
      const fieldErrors = serverFieldErrors(apiError);
      setErrors(fieldErrors);
      setServerError(apiError);
      if (fieldErrors.display_label) labelRef.current?.focus();
      else alertRef.current?.focus();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitParticipant();
  }

  const fieldErrorsShown = hasErrors(errors);
  const statusText = pending ? "Saving…" : serverError ? "Save failed" : "Not saved yet";

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10 lg:px-10 lg:py-12">
      <Link
        to="/app/participants"
        className="inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-slate transition-colors duration-150 hover:text-navy"
      >
        <ArrowLeft size={16} aria-hidden="true" />
        {words.peopleTitle}
      </Link>

      <header className="mt-6 max-w-xl border-b border-border pb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-navy sm:text-3xl">{words.addTitle}</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate">{words.addDescription}</p>
      </header>

      <div className="mt-8 max-w-xl">
        {serverError ? (
          <div ref={alertRef} tabIndex={-1} className="mb-8 rounded-md">
            <Alert
              variant="error"
              title={`Couldn't ${words.add.toLowerCase()}`}
              action={
                fieldErrorsShown ? undefined : (
                  <Button variant="secondary" size="sm" onClick={() => void submitParticipant()} loading={pending}>
                    {pending ? null : <RotateCw size={14} aria-hidden="true" />}
                    Retry
                  </Button>
                )
              }
            >
              {alertMessage(serverError, errors)}
            </Alert>
          </div>
        ) : null}

        <form noValidate autoComplete="off" aria-busy={pending || undefined} onSubmit={handleSubmit}>
          <fieldset className="animate-fade-in flex flex-col gap-6 rounded-lg bg-mist p-6 sm:p-8">
            <legend className="sr-only">{words.addTitle}</legend>
            <TextField
              ref={labelRef}
              label={words.labelField}
              name="display_label"
              required={labelRequired}
              autoComplete="off"
              value={displayLabel}
              error={errors.display_label}
              hint={words.labelHint}
              meta={`${characterCount(displayLabel.trim())}/${LABEL_MAX}`}
              onChange={(event) => {
                setDisplayLabel(event.target.value);
                clearField();
              }}
            />
          </fieldset>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
            <Link
              to="/app/participants"
              aria-disabled={pending || undefined}
              tabIndex={pending ? -1 : undefined}
              onClick={(event) => {
                if (pending) event.preventDefault();
              }}
              className={buttonClasses({
                variant: "ghost",
                className: pending ? "pointer-events-none opacity-60" : "",
              })}
            >
              Cancel
            </Link>
            <div className="flex flex-wrap items-center gap-4">
              <p aria-live="polite" className={`text-sm ${serverError ? "text-red-text" : "text-slate"}`}>
                <span key={statusText} className="animate-fade-in">
                  {statusText}
                </span>
              </p>
              <Button type="submit" loading={pending}>
                {pending ? words.adding : words.add}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
