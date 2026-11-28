import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import { RotateCw, UserPlus, Users } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { Skeleton } from "../../components/ui/Skeleton";
import { buttonClasses } from "../../components/ui/buttonClasses";
import { ApiError, getDashboardSummary, isAbortError } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { formatDate, formatDateTime, formatRelativeTime } from "../../lib/format";
import { formatMembershipRole } from "../../lib/roles";
import type { ActivityItem, DashboardMetric, DashboardModule, DashboardSummary, Me } from "../../lib/types";
import { useDocumentTitle } from "../../lib/useDocumentTitle";
import { activeContext, WORKFLOW_WORDS } from "../../lib/workflow";
import type { WorkflowContext } from "../../lib/workflow";
import { useAuth } from "../auth/authContext";
import {
  fetchParticipants,
  presentRecords,
  readRecentAssessments,
  readRecentParticipants,
} from "./dashboardRecords";
import type { PresentedRecords } from "./dashboardRecords";

type SummaryState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; summary: DashboardSummary; loadedAt: Date };

type ParticipantsState =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "error"; error: unknown }
  | PresentedRecords;

const ADD_PARTICIPANT_PATH = "/app/participants/new";
const SECTION_HEADING = "text-lg font-semibold tracking-tight text-navy";

function isReportedCount(metric: DashboardMetric): metric is DashboardMetric & { value: number } {
  return metric.available && typeof metric.value === "number" && Number.isFinite(metric.value);
}

function metricByKey(metrics: DashboardMetric[], key: DashboardMetric["key"]): DashboardMetric | undefined {
  return metrics.find((metric) => metric.key === key);
}

function countLabel(value: number, singular: string, plural: string): string {
  return `${value.toLocaleString()} ${value === 1 ? singular : plural}`;
}

function listCaption(presented: Extract<PresentedRecords, { status: "ready" }>): string | null {
  if (presented.totalReturned <= presented.records.length) return null;
  const shown = presented.records.length.toLocaleString();
  const total = presented.totalReturned.toLocaleString();
  return presented.sortedByDate
    ? `Showing ${shown} of ${total} records returned, newest first.`
    : `Showing ${shown} of ${total} records returned.`;
}

function AddParticipantLink({ label, prominent = false }: { label: string; prominent?: boolean }) {
  if (prominent) {
    return (
      <Link to={ADD_PARTICIPANT_PATH} className={buttonClasses({ variant: "primary", size: "lg", className: "self-start" })}>
        <UserPlus size={18} aria-hidden="true" />
        {label}
      </Link>
    );
  }
  return (
    <Link
      to={ADD_PARTICIPANT_PATH}
      className="text-sm font-medium text-navy underline decoration-border underline-offset-4 transition-colors duration-200 hover:decoration-navy"
    >
      {label}
    </Link>
  );
}

function DashboardHeader({ me, summary, addLabel }: { me: Me; summary: DashboardSummary | null; addLabel: string }) {
  const name = me.user.display_name || me.user.email;
  const membership = summary?.membership ?? me.membership;
  const workspaceName = summary?.workspace.name ?? me.workspace?.name ?? "Workspace";
  const description = summary?.workspace.description;

  return (
    <header className="flex flex-col gap-8 border-b border-border pb-10 sm:flex-row sm:items-end sm:justify-between lg:flex-col xl:flex-row xl:items-end xl:justify-between">
      <div className="min-w-0 max-w-2xl">
        <p className="text-sm font-medium text-slate">Overview</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-navy sm:text-4xl">{workspaceName}</h1>
        <p className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate">
          <span>{name}</span>
          {membership ? (
            <>
              <span aria-hidden="true">·</span>
              <span>{formatMembershipRole(membership)}</span>
            </>
          ) : null}
          {summary ? (
            <>
              <span aria-hidden="true">·</span>
              <span className="tabular-nums">
                {countLabel(summary.workspace.member_count, "member", "members")}
              </span>
            </>
          ) : null}
        </p>
        {description ? <p className="mt-3 max-w-prose text-sm leading-6 text-slate">{description}</p> : null}
      </div>
      <AddParticipantLink label={addLabel} prominent />
    </header>
  );
}

function MetricFigure({ metric, showNote }: { metric: DashboardMetric; showNote: boolean }) {
  const counted = isReportedCount(metric);
  return (
    <div className="border-t border-border pt-5">
      <dt className="text-sm text-slate">{metric.label}</dt>
      <dd className="mt-3">
        {counted ? (
          <span className="block text-4xl leading-none font-semibold tracking-tight text-navy tabular-nums">
            {metric.value.toLocaleString()}
          </span>
        ) : (
          <>
            <span aria-hidden="true" className="block text-4xl leading-none font-semibold tracking-tight text-slate">
              —
            </span>
            <span className="sr-only">Not available.</span>
          </>
        )}
        {showNote && metric.note ? <p className="mt-3 max-w-xs text-sm leading-5 text-slate">{metric.note}</p> : null}
        {!showNote && !counted && metric.note ? <span className="sr-only">{metric.note}</span> : null}
      </dd>
    </div>
  );
}

function MetricsRow({ metrics }: { metrics: DashboardMetric[] }) {
  const seenNotes = new Set<string>();
  return (
    <section aria-labelledby="metrics-heading">
      <h2 id="metrics-heading" className="sr-only">
        Workspace metrics
      </h2>
      <dl className="grid grid-cols-1 gap-x-12 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((metric) => {
          const counted = isReportedCount(metric);
          const note = !counted && metric.note ? metric.note : null;
          const showNote = note !== null && !seenNotes.has(note);
          if (note !== null) seenNotes.add(note);
          return <MetricFigure key={metric.key} metric={metric} showNote={showNote || (counted && Boolean(metric.note))} />;
        })}
      </dl>
    </section>
  );
}

function RecordRows({
  presented,
  pathForId,
}: {
  presented: Extract<PresentedRecords, { status: "ready" }>;
  pathForId?: (id: string) => string;
}) {
  const caption = listCaption(presented);
  return (
    <>
      <ol className="mt-6 divide-y divide-border border-y border-border">
        {presented.records.map((record, index) => {
          const to = pathForId?.(record.id);
          const body = (
            <>
              <div className="min-w-0">
                <p className="truncate font-medium text-navy">{record.label}</p>
                {record.detail ? <p className="mt-1 truncate text-sm text-slate">{record.detail}</p> : null}
              </div>
              {record.occurredAt ? (
                <time dateTime={record.occurredAt} className="shrink-0 text-sm text-slate tabular-nums">
                  {formatDate(record.occurredAt)}
                </time>
              ) : null}
            </>
          );
          return (
            <li key={`${record.id}-${index}`}>
              {to ? (
                <Link
                  to={to}
                  className="-mx-3 flex items-baseline justify-between gap-6 rounded-md px-3 py-4 transition-colors duration-200 hover:bg-mist"
                >
                  {body}
                </Link>
              ) : (
                <div className="flex items-baseline justify-between gap-6 py-4">{body}</div>
              )}
            </li>
          );
        })}
      </ol>
      {caption ? <p className="mt-3 text-xs text-slate">{caption}</p> : null}
    </>
  );
}

function participantUnavailableCopy(
  metric: DashboardMetric | undefined,
  context: WorkflowContext,
): { title: string; description: string } {
  const words = WORKFLOW_WORDS[context];
  if (metric && isReportedCount(metric)) {
    return metric.value === 0
      ? {
          title: words.recentEmptyTitle,
          description: "The workspace count is zero, and a record list was not returned.",
        }
      : {
          title: `${words.personTitle} list was not returned`,
          description: `${countLabel(metric.value, `${words.person} is`, `${words.people} are`)} counted for this workspace.`,
        };
  }
  return {
    title: `No ${words.person} records listed`,
    description: words.recentEmptyDescription,
  };
}

function participantEmptyCopy(
  metric: DashboardMetric | undefined,
  context: WorkflowContext,
): { title: string; description: string } {
  const words = WORKFLOW_WORDS[context];
  if (metric && isReportedCount(metric) && metric.value > 0) {
    return {
      title: "No recent records returned",
      description: `${countLabel(metric.value, `${words.person} is`, `${words.people} are`)} counted for this workspace. The recent list was empty.`,
    };
  }
  if (metric && isReportedCount(metric)) {
    return {
      title: words.recentEmptyTitle,
      description: words.recentEmptyDescription,
    };
  }
  return {
    title: `No ${words.people} returned`,
    description: `The ${words.person} list is empty.`,
  };
}

function RecentParticipants({
  metrics,
  state,
  onRetry,
  context,
}: {
  metrics: DashboardMetric[];
  state: ParticipantsState;
  onRetry: () => void;
  context: WorkflowContext;
}) {
  const words = WORKFLOW_WORDS[context];
  const metric = metricByKey(metrics, context === "clinical" ? "patients" : "participants");
  return (
    <section aria-labelledby="participants-heading">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="participants-heading" className={SECTION_HEADING}>
          {words.recentTitle}
        </h2>
        {state.status === "ready" || state.status === "empty" ? (
          <Link
            to="/app/participants"
            className="text-sm font-medium text-navy underline decoration-border underline-offset-4 transition-colors duration-200 hover:decoration-navy"
          >
            All {words.people}
          </Link>
        ) : null}
      </div>
      {state.status === "loading" ? (
        <div className="mt-6 flex flex-col gap-3" aria-busy="true">
          <span className="sr-only" role="status">
            Loading {words.people}
          </span>
          <Skeleton className="h-14" />
          <Skeleton className="h-14" />
        </div>
      ) : null}
      {state.status === "error" ? (
        <Alert
          variant="error"
          title={`Couldn't load ${words.people}`}
          className="mt-6"
          action={
            <Button variant="secondary" size="sm" onClick={onRetry}>
              <RotateCw size={14} aria-hidden="true" />
              Retry
            </Button>
          }
        >
          {getErrorMessage(state.error)}
        </Alert>
      ) : null}
      {state.status === "unavailable" ? (
        <div className="mt-6">
          <EmptyState icon={Users} {...participantUnavailableCopy(metric, context)} action={<AddParticipantLink label={words.add} />} />
        </div>
      ) : null}
      {state.status === "empty" ? (
        <div className="mt-6">
          <EmptyState icon={Users} {...participantEmptyCopy(metric, context)} action={<AddParticipantLink label={words.add} />} />
        </div>
      ) : null}
      {state.status === "ready" ? (
        <RecordRows presented={state} pathForId={(id) => `/app/participants/${encodeURIComponent(id)}`} />
      ) : null}
    </section>
  );
}

function assessmentProse(metrics: DashboardMetric[], embeddedEmpty: boolean): string {
  const assessments = metricByKey(metrics, "assessments");
  const inProgress = metricByKey(metrics, "assessments_in_progress");
  const review = metricByKey(metrics, "assessments_needing_review");
  const sentences: string[] = [];

  if (assessments && isReportedCount(assessments) && assessments.value === 0) {
    sentences.push("No assessments have been recorded.");
  } else if (embeddedEmpty) {
    sentences.push("The summary included no assessment records.");
  } else if (assessments && isReportedCount(assessments)) {
    sentences.push(
      `${countLabel(assessments.value, "assessment is", "assessments are")} recorded. This summary does not include each record.`,
    );
  } else {
    sentences.push("Individual assessment records are not included in this summary.");
  }

  if (inProgress && isReportedCount(inProgress)) {
    sentences.push(
      inProgress.value === 0
        ? "None are in progress."
        : `${countLabel(inProgress.value, "assessment is", "assessments are")} in progress.`,
    );
  }
  if (review && isReportedCount(review)) {
    sentences.push(
      review.value === 0
        ? "Nothing is waiting for review."
        : `${countLabel(review.value, "assessment needs", "assessments need")} review.`,
    );
  }
  return sentences.join(" ");
}

function RecentAssessments({ summary }: { summary: DashboardSummary }) {
  const embedded = readRecentAssessments(summary);
  const presented = embedded.kind === "records" ? presentRecords(embedded.records) : null;
  return (
    <section aria-labelledby="assessments-heading">
      <h2 id="assessments-heading" className={SECTION_HEADING}>
        Recent assessments
      </h2>
      {embedded.kind === "unreadable" ? (
        <p className="mt-4 max-w-prose text-sm leading-6 text-slate">
          Assessment records were included in the summary but could not be read.
        </p>
      ) : null}
      {presented?.status === "ready" ? <RecordRows presented={presented} /> : null}
      {presented?.status === "empty" || embedded.kind === "absent" ? (
        <p className="mt-4 max-w-prose text-sm leading-6 text-slate">
          {assessmentProse(summary.metrics, presented?.status === "empty")}
        </p>
      ) : null}
    </section>
  );
}

function StudiesSection({ modules }: { modules: DashboardModule[] }) {
  const studies = modules.find((module) => module.key === "studies");
  const copy = studies
    ? studies.available
      ? "Studies are enabled for this workspace. This summary does not list them."
      : studies.note
    : "This summary does not include studies.";
  return (
    <section aria-labelledby="studies-heading">
      <h2 id="studies-heading" className={SECTION_HEADING}>
        Studies
      </h2>
      <p className="mt-4 max-w-prose text-sm leading-6 text-slate">{copy}</p>
    </section>
  );
}

function WorkspacePanel({ summary }: { summary: DashboardSummary }) {
  const { workspace, membership } = summary;
  const rows: Array<[string, string]> = [
    ["Name", workspace.name],
    ["Description", workspace.description || "No description"],
    ["Created", formatDate(workspace.created_at)],
    ["Members", workspace.member_count.toLocaleString()],
    ["Your role", formatMembershipRole(membership)],
  ];
  return (
    <section aria-labelledby="workspace-heading" className="rounded-lg bg-mist px-6 py-6">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="workspace-heading" className={SECTION_HEADING}>
          Workspace
        </h2>
        <Link
          to="/setup"
          className="rounded text-sm font-medium text-navy underline decoration-border underline-offset-4 transition-colors duration-200 hover:decoration-navy"
        >
          Edit details
        </Link>
      </div>
      <dl className="mt-5 flex flex-col gap-4 text-sm">
        {rows.map(([term, value]) => (
          <div key={term} className="flex flex-col gap-0.5">
            <dt className="text-xs text-slate">{term}</dt>
            <dd className={`break-words text-navy ${term === "Members" ? "tabular-nums" : ""}`}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function RecentActivity({ items, now }: { items: ActivityItem[]; now: Date }) {
  return (
    <section aria-labelledby="activity-heading">
      <h2 id="activity-heading" className={SECTION_HEADING}>
        Recent activity
      </h2>
      {items.length === 0 ? (
        <p className="mt-4 text-sm leading-6 text-slate">No activity recorded yet.</p>
      ) : (
        <ol className="mt-5 flex flex-col gap-5">
          {items.map((item) => (
            <li key={item.id} className="flex gap-3">
              <span aria-hidden="true" className="mt-1.5 size-2 shrink-0 rounded-full bg-navy" />
              <div className="min-w-0">
                <p className="text-sm leading-5 break-words text-navy">{item.title}</p>
                <p className="mt-1 text-xs text-slate">
                  <time dateTime={item.occurred_at} title={formatDateTime(item.occurred_at)}>
                    {formatRelativeTime(item.occurred_at, now)}
                  </time>
                  <span aria-hidden="true"> · </span>
                  <span>{formatDateTime(item.occurred_at)}</span>
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div aria-busy="true" className="mt-12 flex flex-col gap-16">
      <span className="sr-only" role="status">
        Loading dashboard
      </span>
      <div className="grid grid-cols-1 gap-10 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-28" />
        ))}
      </div>
      <div className="grid gap-16 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-4">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-40" />
        </div>
        <Skeleton className="h-72" />
      </div>
    </div>
  );
}

function participantsFromSummary(summary: DashboardSummary): ParticipantsState | null {
  const embedded = readRecentParticipants(summary);
  if (embedded.kind === "absent") return null;
  if (embedded.kind === "unreadable") {
    return {
      status: "error",
      error: new ApiError(200, "unexpected_response", "The participant list could not be read."),
    };
  }
  return presentRecords(embedded.records);
}

export function DashboardPage() {
  const { me, expireSession, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [summaryState, setSummaryState] = useState<SummaryState>({ status: "loading" });
  const [participantsState, setParticipantsState] = useState<ParticipantsState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  useDocumentTitle("Overview");

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setSummaryState({ status: "loading" });
    setParticipantsState({ status: "loading" });

    async function load() {
      try {
        const summary = await getDashboardSummary(controller.signal);
        if (!active) return;
        setSummaryState({ status: "ready", summary, loadedAt: new Date() });

        const embedded = participantsFromSummary(summary);
        if (embedded !== null) {
          setParticipantsState(embedded);
          return;
        }

        try {
          const list = await fetchParticipants(controller.signal);
          if (!active) return;
          setParticipantsState(list);
        } catch (error) {
          if (!active || isAbortError(error)) return;
          if (isUnauthorized(error)) {
            expireSession();
            return;
          }
          setParticipantsState({ status: "error", error });
        }
      } catch (error) {
        if (!active || isAbortError(error)) return;
        if (isUnauthorized(error)) {
          expireSession();
          return;
        }
        if (error instanceof ApiError && error.code === "workspace_not_found") {
          await refreshMe();
          if (!active) return;
          navigate("/setup", { replace: true });
          return;
        }
        setSummaryState({ status: "error", error });
      }
    }

    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [reloadKey, expireSession, refreshMe, navigate]);

  function retry() {
    setReloadKey((key) => key + 1);
  }

  if (me === null) return null;
  const context = activeContext(me.membership);
  const words = WORKFLOW_WORDS[context];
  const summary = summaryState.status === "ready" ? summaryState.summary : null;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-12 sm:px-8 lg:px-10 lg:py-16">
      <DashboardHeader me={me} summary={summary} addLabel={words.add} />
      {summaryState.status === "loading" ? <DashboardSkeleton /> : null}
      {summaryState.status === "error" ? (
        <Alert
          variant="error"
          title="Couldn't load the dashboard"
          className="mt-12"
          action={
            <Button variant="secondary" size="sm" onClick={retry}>
              <RotateCw size={14} aria-hidden="true" />
              Retry
            </Button>
          }
        >
          {getErrorMessage(summaryState.error)}
        </Alert>
      ) : null}
      {summaryState.status === "ready" ? (
        <div className="mt-12 flex flex-col gap-16 motion-safe:animate-fade-in">
          <MetricsRow metrics={summaryState.summary.metrics} />
          <div className="grid gap-16 xl:grid-cols-[minmax(0,1fr)_22rem]">
            <div className="flex min-w-0 flex-col gap-16">
              <RecentParticipants
                metrics={summaryState.summary.metrics}
                state={participantsState}
                onRetry={retry}
                context={context}
              />
              <RecentAssessments summary={summaryState.summary} />
              <StudiesSection modules={summaryState.summary.modules} />
            </div>
            <aside aria-label="Workspace summary" className="flex flex-col gap-12">
              <WorkspacePanel summary={summaryState.summary} />
              <RecentActivity items={summaryState.summary.recent_activity} now={summaryState.loadedAt} />
            </aside>
          </div>
        </div>
      ) : null}
    </div>
  );
}
