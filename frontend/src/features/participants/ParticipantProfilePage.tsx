import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { ArrowLeft, History, RotateCw } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Skeleton } from "../../components/ui/Skeleton";
import { buttonClasses } from "../../components/ui/buttonClasses";
import { ApiError, isAbortError, NETWORK_ERROR_MESSAGE } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { formatDate, formatDateTime } from "../../lib/format";
import { activeContext, personLabel, WORKFLOW_WORDS } from "../../lib/workflow";
import { useDocumentTitle } from "../../lib/useDocumentTitle";
import { withHandoffQuery } from "../assessments/assessmentDraft";
import { useAuth } from "../auth/authContext";

export type AssessmentRecord = {
  id: string;
  modality: string | null;
  protocol: string | null;
  status: string | null;
  recordedAt: string | null;
};

export type ParticipantRecord = {
  id: string;
  context: "clinical" | "research";
  referenceCode: string | null;
  displayLabel: string | null;
  createdAt: string;
  assessments: AssessmentRecord[];
};

type ParticipantView =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "error"; error: unknown }
  | { status: "ready"; participant: ParticipantRecord };

type StoredView =
  | { status: "idle" }
  | { status: "not_found"; forId: string; reloadKey: number }
  | { status: "error"; forId: string; reloadKey: number; error: unknown }
  | { status: "ready"; forId: string; reloadKey: number; participant: ParticipantRecord };

const UNEXPECTED_RESPONSE = "The server returned an unexpected response.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function toApiError(status: number, body: unknown): ApiError {
  if (isRecord(body) && isRecord(body.error)) {
    const code = body.error.code;
    const message = body.error.message;
    if (typeof code === "string" && typeof message === "string") return new ApiError(status, code, message);
  }
  return new ApiError(status, "unexpected_response", UNEXPECTED_RESPONSE);
}

function readAssessments(source: Record<string, unknown>): AssessmentRecord[] {
  // This payload does not include assessments. An omitted, null, or empty list
  // is an empty history — rows are rendered only from objects the API actually sent.
  const value = source.assessments;
  if (value === undefined || value === null) return [];
  const list = Array.isArray(value) ? value : isRecord(value) && Array.isArray(value.items) ? value.items : null;
  if (list === null) return [];

  const records: AssessmentRecord[] = [];
  for (const item of list) {
    if (!isRecord(item)) continue;
    const id = readString(item, "id") ?? readString(item, "assessment_id");
    if (id === null) continue;
    records.push({
      id,
      modality: readString(item, "modality"),
      protocol: readString(item, "protocol_name") ?? readString(item, "protocol"),
      status: readString(item, "status"),
      recordedAt:
        readString(item, "recorded_at") ??
        readString(item, "completed_at") ??
        readString(item, "created_at") ??
        readString(item, "started_at"),
    });
  }
  return records;
}

function parseParticipant(value: unknown): ParticipantRecord {
  const body = isRecord(value) ? value : null;
  const nested = body !== null && isRecord(body.participant) ? body.participant : null;
  const record = body !== null && (typeof body.reference_code === "string" || body.reference_code === null) ? body : nested;
  if (record === null || !isRecord(record)) throw new ApiError(500, "unexpected_response", UNEXPECTED_RESPONSE);

  const id = readString(record, "id");
  const referenceCode = readString(record, "reference_code");
  const displayLabel = readString(record, "display_label");
  const createdAt = readString(record, "created_at");
  const context = record.context === "clinical" || record.context === "research" ? record.context : null;
  if (id === null || createdAt === null || context === null || (referenceCode === null && displayLabel === null)) {
    throw new ApiError(500, "unexpected_response", UNEXPECTED_RESPONSE);
  }

  return {
    id,
    context,
    referenceCode,
    displayLabel,
    createdAt,
    assessments: readAssessments(record),
  };
}

async function loadParticipant(id: string, signal: AbortSignal): Promise<ParticipantRecord> {
  let response: Response;
  try {
    response = await fetch(`/api/participants/${encodeURIComponent(id)}`, {
      credentials: "include",
      headers: { Accept: "application/json" },
      signal,
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError(0, "network_error", NETWORK_ERROR_MESSAGE);
  }

  let parsed: unknown;
  try {
    parsed = await response.json();
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new ApiError(0, "network_error", NETWORK_ERROR_MESSAGE);
  }

  if (!response.ok) throw toApiError(response.status, parsed);
  return parseParticipant(parsed);
}

export function participantPath(id: string, suffix = ""): string {
  return `/app/participants/${encodeURIComponent(id)}${suffix}`;
}

export function useParticipantRecord(participantId: string | undefined): {
  view: ParticipantView;
  retry: () => void;
} {
  const { expireSession, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [reloadKey, setReloadKey] = useState(0);
  const [stored, setStored] = useState<StoredView>({ status: "idle" });
  const id = participantId?.trim() ?? "";
  const retry = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    if (id === "") return;
    const controller = new AbortController();
    const requestId = id;
    const requestKey = reloadKey;

    loadParticipant(requestId, controller.signal)
      .then((participant) => {
        if (controller.signal.aborted) return;
        setStored({ status: "ready", forId: requestId, reloadKey: requestKey, participant });
      })
      .catch(async (error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) return;
        if (isUnauthorized(error)) {
          expireSession();
          return;
        }
        // 404 is a missing or out-of-workspace participant. 422 is an id the API rejects.
        if (error instanceof ApiError && (error.status === 404 || error.status === 422)) {
          setStored({ status: "not_found", forId: requestId, reloadKey: requestKey });
          return;
        }
        if (error instanceof ApiError && error.code === "workspace_not_found") {
          try {
            await refreshMe();
          } catch {
            if (!controller.signal.aborted) {
              setStored({ status: "error", forId: requestId, reloadKey: requestKey, error });
            }
            return;
          }
          if (!controller.signal.aborted) navigate("/setup", { replace: true });
          return;
        }
        setStored({ status: "error", forId: requestId, reloadKey: requestKey, error });
      });

    return () => controller.abort();
  }, [id, reloadKey, expireSession, refreshMe, navigate]);

  const current = stored.status !== "idle" && stored.forId === id && stored.reloadKey === reloadKey ? stored : null;
  let view: ParticipantView;
  if (id === "") view = { status: "not_found" };
  else if (current === null) view = { status: "loading" };
  else if (current.status === "not_found") view = { status: "not_found" };
  else if (current.status === "error") view = { status: "error", error: current.error };
  else view = { status: "ready", participant: current.participant };

  return { view, retry };
}

export function ParticipantScreen({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-6xl px-6 py-10 lg:px-10 lg:py-12">{children}</div>;
}

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex max-w-full items-center gap-1.5 rounded-md text-sm font-medium text-slate transition-colors duration-150 hover:text-navy"
    >
      <ArrowLeft size={16} aria-hidden="true" className="shrink-0" />
      <span className="min-w-0 break-words">{children}</span>
    </Link>
  );
}

export function ParticipantPageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="border-b border-border pb-8">
      <div className="max-w-2xl min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight break-words text-navy sm:text-3xl">{title}</h1>
        {description ? <div className="mt-2 text-sm break-words text-slate">{description}</div> : null}
        {actions ? <div className="mt-6 flex flex-wrap items-start gap-4">{actions}</div> : null}
      </div>
    </header>
  );
}

export function ParticipantContentSkeleton({
  label,
  withAction = false,
}: {
  label: string;
  withAction?: boolean;
}) {
  return (
    <div aria-busy="true" className="flex flex-col gap-8">
      <span role="status" className="sr-only">
        {label}
      </span>
      <div className="flex max-w-2xl flex-col gap-3 border-b border-border pb-8">
        <Skeleton className="h-9 w-52 max-w-full" />
        <Skeleton className="h-4 w-72 max-w-full" />
        {withAction ? <Skeleton className="mt-3 h-10 w-48" /> : null}
      </div>
      <Skeleton className="h-44 max-w-2xl" />
    </div>
  );
}

export function ParticipantNotFound() {
  const { me } = useAuth();
  const words = WORKFLOW_WORDS[activeContext(me?.membership)];
  return (
    <div className="max-w-md animate-fade-in motion-reduce:animate-none">
      <p className="text-sm font-medium text-slate">404</p>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight text-navy sm:text-3xl">{words.notFoundTitle}</h1>
      <p className="mt-2 max-w-prose text-sm text-slate">{words.notFoundBody}</p>
      <Link to="/app/participants" className={buttonClasses({ className: "mt-8" })}>
        Back to {words.people}
      </Link>
    </div>
  );
}

export function ParticipantLoadError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div className="max-w-2xl animate-fade-in motion-reduce:animate-none">
      <h1 className="text-2xl font-semibold tracking-tight text-navy sm:text-3xl">Couldn't load this participant</h1>
      <Alert
        variant="error"
        className="mt-6"
        action={
          <Button variant="secondary" size="sm" onClick={onRetry}>
            <RotateCw size={14} aria-hidden="true" />
            Retry
          </Button>
        }
      >
        {getErrorMessage(error)}
      </Alert>
    </div>
  );
}

function Detail({ term, children, muted = false }: { term: string; children: ReactNode; muted?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs text-slate">{term}</dt>
      <dd className={`text-sm break-words ${muted ? "text-slate" : "font-medium text-navy"}`}>{children}</dd>
    </div>
  );
}

function ProfileReady({ participant }: { participant: ParticipantRecord }) {
  const [searchParams] = useSearchParams();
  const startAssessment = withHandoffQuery(
    participantPath(participant.id, "/assessments/new"),
    searchParams.toString(),
  );
  return (
    <div className="animate-fade-in motion-reduce:animate-none">
      <ParticipantPageHeader
        title={personLabel({ reference_code: participant.referenceCode, display_label: participant.displayLabel })}
        description={
          participant.referenceCode && participant.displayLabel ? (
            <span className="font-medium text-navy">{participant.displayLabel}</span>
          ) : undefined
        }
        actions={
          <>
            <Link to={startAssessment} className={buttonClasses()}>
              Start assessment
            </Link>
            <Link to={participantPath(participant.id, "/history")} className={buttonClasses({ variant: "secondary" })}>
              <History size={16} aria-hidden="true" />
              Assessment history
            </Link>
          </>
        }
      />
      <section
        aria-labelledby="participant-details-heading"
        className="mt-12 max-w-2xl rounded-lg bg-mist px-6 py-8 sm:px-8"
      >
        <h2 id="participant-details-heading" className="text-base font-semibold text-navy">
          Details
        </h2>
        <dl className="mt-6 flex flex-col gap-6">
          <Detail term={participant.context === "clinical" ? "Name or label" : "Participant code"}>
            {participant.referenceCode ?? participant.displayLabel ?? "Not recorded"}
          </Detail>
          {participant.referenceCode ? (
            <Detail term="Label" muted={participant.displayLabel === null}>
              {participant.displayLabel ?? "No label"}
            </Detail>
          ) : null}
          <Detail term="Created">
            <time dateTime={participant.createdAt} title={formatDateTime(participant.createdAt)}>
              {formatDate(participant.createdAt)}
            </time>
          </Detail>
        </dl>
      </section>
    </div>
  );
}

export function ParticipantProfilePage() {
  const { id } = useParams();
  const { me } = useAuth();
  const words = WORKFLOW_WORDS[activeContext(me?.membership)];
  const { view, retry } = useParticipantRecord(id);
  const title =
    view.status === "not_found"
      ? words.notFoundTitle
      : view.status === "ready"
        ? personLabel({
            reference_code: view.participant.referenceCode,
            display_label: view.participant.displayLabel,
          })
        : words.personTitle;
  useDocumentTitle(title);

  return (
    <ParticipantScreen>
      {view.status !== "not_found" ? (
        <div className="mb-8">
          <BackLink to="/app/participants">{words.peopleTitle}</BackLink>
        </div>
      ) : null}
      {view.status === "loading" ? <ParticipantContentSkeleton label="Loading participant" withAction /> : null}
      {view.status === "not_found" ? <ParticipantNotFound /> : null}
      {view.status === "error" ? <ParticipantLoadError error={view.error} onRetry={retry} /> : null}
      {view.status === "ready" ? <ProfileReady participant={view.participant} /> : null}
    </ParticipantScreen>
  );
}
