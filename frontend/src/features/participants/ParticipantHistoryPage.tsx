import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { ClipboardList, RotateCw } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { ApiError, getParticipantHistory, isAbortError } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { formatDate, formatDateTime } from "../../lib/format";
import type { AssessmentHistoryItem } from "../../lib/types";
import { useDocumentTitle } from "../../lib/useDocumentTitle";
import { personLabel, WORKFLOW_WORDS } from "../../lib/workflow";
import { useAuth } from "../auth/authContext";
import type { ParticipantRecord } from "./ParticipantProfilePage";
import {
  BackLink,
  ParticipantContentSkeleton,
  ParticipantLoadError,
  ParticipantNotFound,
  ParticipantPageHeader,
  ParticipantScreen,
  participantPath,
  useParticipantRecord,
} from "./ParticipantProfilePage";

function formatStatus(status: string): string {
  if (/\s/.test(status)) return status;
  const words = status.replaceAll("_", " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function recordedLabel(count: number): string {
  return count === 1 ? "1 assessment recorded" : `${count.toLocaleString()} assessments recorded`;
}

function sessionHref(item: AssessmentHistoryItem): string {
  if (item.status === "completed") return `/app/sessions/${item.id}/results`;
  if (item.status === "awaiting_review") return `/app/sessions/${item.id}/review`;
  return `/app/sessions/${item.id}`;
}

function sessionAction(status: string): string {
  if (status === "completed") return "Results";
  if (status === "awaiting_review") return "Review";
  return "Resume";
}

function AssessmentRow({ assessment }: { assessment: AssessmentHistoryItem }) {
  const title = assessment.protocol_label ?? "Assessment";
  const details = [
    assessment.protocol_version ? `Version ${assessment.protocol_version}` : null,
    formatStatus(assessment.status),
    assessment.visit_label ? `Visit: ${assessment.visit_label}` : null,
    assessment.study_name ? `Study: ${assessment.study_name}` : null,
  ].filter((part): part is string => part !== null && part !== title);

  return (
    <li>
      <Link
        to={sessionHref(assessment)}
        className="flex flex-col gap-1 rounded-md px-6 py-5 transition-colors duration-150 hover:bg-mist focus-visible:bg-mist motion-reduce:transition-none sm:flex-row sm:items-baseline sm:justify-between sm:gap-8"
      >
        <div className="min-w-0">
          <p className="text-sm font-medium break-words text-navy">{title}</p>
          {details.length > 0 ? <p className="mt-0.5 text-xs break-words text-slate">{details.join(" · ")}</p> : null}
        </div>
        <span className="flex shrink-0 items-baseline gap-4">
          <span className="text-sm font-medium text-navy">{sessionAction(assessment.status)}</span>
          <time dateTime={assessment.created_at} title={formatDateTime(assessment.created_at)} className="text-sm text-slate">
            {formatDate(assessment.created_at)}
          </time>
        </span>
      </Link>
    </li>
  );
}

function HistoryReady({
  participant,
  assessments,
}: {
  participant: ParticipantRecord;
  assessments: AssessmentHistoryItem[];
}) {
  const identity = personLabel({
    reference_code: participant.referenceCode,
    display_label: participant.displayLabel,
  });
  return (
    <div className="animate-fade-in motion-reduce:animate-none">
      <ParticipantPageHeader
        title="Assessment history"
        description={
          <span className="break-words">
            <span className="font-medium text-navy">{identity}</span>
            {participant.referenceCode && participant.displayLabel ? (
              <>
                <span aria-hidden="true"> · </span>
                {participant.displayLabel}
              </>
            ) : null}
          </span>
        }
      />
      {assessments.length === 0 ? (
        <div className="mt-12 max-w-2xl">
          <EmptyState
            icon={ClipboardList}
            title="No assessments recorded"
            description={WORKFLOW_WORDS[participant.context].historyEmpty}
          />
        </div>
      ) : (
        <section aria-labelledby="recorded-assessments-heading" className="mt-12 max-w-3xl">
          <h2 id="recorded-assessments-heading" className="text-base font-semibold text-navy">
            Recorded assessments
          </h2>
          <p className="mt-1 text-sm text-slate">{recordedLabel(assessments.length)}</p>
          <ol className="mt-4 list-none divide-y divide-border rounded-lg border border-border">
            {assessments.map((assessment, index) => (
              <AssessmentRow key={`${assessment.id}-${index}`} assessment={assessment} />
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}

export function ParticipantHistoryPage() {
  const { id } = useParams();
  const { expireSession } = useAuth();
  const { view, retry } = useParticipantRecord(id);
  const [history, setHistory] = useState<AssessmentHistoryItem[] | null>(null);
  const [historyError, setHistoryError] = useState<unknown>(null);
  const [historyReload, setHistoryReload] = useState(0);
  useDocumentTitle(view.status === "not_found" ? "Participant not found" : "Assessment history");

  useEffect(() => {
    if (!id || view.status !== "ready") return;
    const controller = new AbortController();
    setHistory(null);
    setHistoryError(null);
    getParticipantHistory(id, controller.signal)
      .then((payload) => {
        if (!controller.signal.aborted) setHistory(payload.items);
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) return;
        if (isUnauthorized(error)) {
          expireSession();
          return;
        }
        setHistoryError(error);
      });
    return () => controller.abort();
  }, [id, view.status, historyReload, expireSession]);

  return (
    <ParticipantScreen>
      {id && view.status !== "not_found" ? (
        <div className="mb-8">
          <BackLink to={participantPath(id)}>
            {view.status === "ready"
              ? personLabel({
                  reference_code: view.participant.referenceCode,
                  display_label: view.participant.displayLabel,
                })
              : "Profile"}
          </BackLink>
        </div>
      ) : null}
      {view.status === "loading" || (view.status === "ready" && history === null && historyError === null) ? (
        <ParticipantContentSkeleton label="Loading assessment history" />
      ) : null}
      {view.status === "not_found" ? <ParticipantNotFound /> : null}
      {view.status === "error" ? <ParticipantLoadError error={view.error} onRetry={retry} /> : null}
      {view.status === "ready" && historyError !== null ? (
        <Alert variant="error" title={historyError instanceof ApiError && historyError.status === 404 ? "Person not found" : "Assessment history is unavailable"}>
          <p>{getErrorMessage(historyError)}</p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => {
              setHistoryError(null);
              setHistoryReload((value) => value + 1);
            }}
          >
            <RotateCw aria-hidden="true" />
            Try again
          </Button>
        </Alert>
      ) : null}
      {view.status === "ready" && history !== null ? <HistoryReady participant={view.participant} assessments={history} /> : null}
    </ParticipantScreen>
  );
}
