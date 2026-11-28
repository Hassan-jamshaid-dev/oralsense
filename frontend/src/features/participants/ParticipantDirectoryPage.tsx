import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { ChevronDown, ChevronRight, RotateCw, Search, UserPlus, Users, X } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/buttonClasses";
import { EmptyState } from "../../components/ui/EmptyState";
import { PageHeader } from "../../components/ui/PageHeader";
import { Skeleton } from "../../components/ui/Skeleton";
import { ApiError, getParticipants, isAbortError } from "../../lib/api";
import { getErrorMessage, isUnauthorized } from "../../lib/errorMessages";
import { formatDate, formatDateTime } from "../../lib/format";
import type { Participant } from "../../lib/types";
import { useDocumentTitle } from "../../lib/useDocumentTitle";
import { activeContext, personLabel, WORKFLOW_WORDS } from "../../lib/workflow";
import { withHandoffQuery } from "../assessments/assessmentDraft";
import { useAuth } from "../auth/authContext";

/** Matches the API whitelist. Anything else in the URL is ignored and never requested. */
const SORT_OPTIONS = [
  { value: "reference_code", label: "Reference code, A to Z" },
  { value: "-reference_code", label: "Reference code, Z to A" },
  { value: "display_label", label: "Display label, A to Z" },
  { value: "-display_label", label: "Display label, Z to A" },
  { value: "-created_at", label: "Recently added" },
  { value: "created_at", label: "Oldest first" },
] as const;

type ParticipantSort = (typeof SORT_OPTIONS)[number]["value"];

const DEFAULT_SORT: ParticipantSort = "reference_code";
const PAGE_SIZE = 25;
const MAX_PAGE = 10_000;
const SEARCH_DEBOUNCE_MS = 250;

const CONTROL =
  "w-full rounded-md border border-border bg-white text-sm text-navy transition-colors duration-150 " +
  "placeholder:text-slate hover:border-slate focus-visible:border-navy";

type ParticipantList = {
  items: Participant[];
  page: number;
  page_size: number;
  total: number;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; list: ParticipantList };

function isSort(value: string | null): value is ParticipantSort {
  return SORT_OPTIONS.some((option) => option.value === value);
}

function parsePage(value: string | null): number {
  if (value === null || value === "") return 1;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1) return 1;
  return Math.min(parsed, MAX_PAGE);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readParticipant(value: unknown): Participant | null {
  if (!isRecord(value)) return null;
  const {
    id,
    context,
    reference_code: referenceCode,
    display_label: label,
    created_at: createdAt,
    updated_at: updatedAt,
  } = value;
  if (typeof id !== "string" || id.length === 0) return null;
  if (context !== "clinical" && context !== "research") return null;
  if (typeof createdAt !== "string" || createdAt.length === 0) return null;
  if (typeof updatedAt !== "string" || updatedAt.length === 0) return null;
  if (referenceCode !== null && typeof referenceCode !== "string") return null;
  if (label !== null && label !== undefined && typeof label !== "string") return null;
  const code = typeof referenceCode === "string" && referenceCode.length > 0 ? referenceCode : null;
  const displayLabel = typeof label === "string" && label.trim().length > 0 ? label : null;
  if (code === null && displayLabel === null) return null;
  return {
    id,
    context,
    reference_code: code,
    display_label: displayLabel,
    created_at: createdAt,
    updated_at: updatedAt,
  };
}

function readParticipantList(value: unknown): ParticipantList | null {
  if (!isRecord(value) || !Array.isArray(value.items)) return null;
  const items: Participant[] = [];
  for (const item of value.items) {
    const participant = readParticipant(item);
    if (participant === null) return null;
    items.push(participant);
  }
  const { page, page_size: pageSize, total } = value;
  if (typeof page !== "number" || !Number.isInteger(page) || page < 1) return null;
  if (typeof pageSize !== "number" || !Number.isInteger(pageSize) || pageSize < 1) return null;
  if (typeof total !== "number" || !Number.isInteger(total) || total < 0) return null;
  return { items, page, page_size: pageSize, total };
}

function writeParams(
  current: URLSearchParams,
  changes: { q?: string; sort?: ParticipantSort; page?: number },
): URLSearchParams {
  const next = new URLSearchParams(current);
  if (changes.q !== undefined) {
    if (changes.q.length > 0) next.set("q", changes.q);
    else next.delete("q");
  }
  if (changes.sort !== undefined) {
    if (changes.sort === DEFAULT_SORT) next.delete("sort");
    else next.set("sort", changes.sort);
  }
  if (changes.page !== undefined) {
    if (changes.page <= 1) next.delete("page");
    else next.set("page", String(changes.page));
  }
  return next;
}

function AddParticipantLink({ label, size = "md" }: { label: string; size?: "sm" | "md" }) {
  return (
    <Link to="/app/participants/new" className={buttonClasses({ variant: "primary", size })}>
      <UserPlus size={16} aria-hidden="true" />
      {label}
    </Link>
  );
}

function DirectorySkeleton({ label }: { label: string }) {
  return (
    <div aria-busy="true" className="mt-10 overflow-hidden rounded-lg border border-border">
      <span className="sr-only" role="status">
        {label}
      </span>
      {Array.from({ length: 6 }, (_, index) => (
        <div key={index} className="border-b border-border px-6 py-6 last:border-b-0">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="mt-3 h-4 w-56" />
        </div>
      ))}
    </div>
  );
}

function DisplayLabel({ label }: { label: string | null }) {
  if (label) return <span className="text-navy">{label}</span>;
  return (
    <>
      <span aria-hidden="true" className="text-slate">
        —
      </span>
      <span className="sr-only">No display label</span>
    </>
  );
}

function ParticipantRow({ participant }: { participant: Participant }) {
  const [searchParams] = useSearchParams();
  const added = formatDate(participant.created_at);
  const addedExact = formatDateTime(participant.created_at);
  return (
    <li className="border-b border-border last:border-b-0">
      <Link
        to={withHandoffQuery(`/app/participants/${participant.id}`, searchParams.toString())}
        className="flex flex-col gap-1 px-6 py-6 transition-colors duration-200 hover:bg-mist focus-visible:bg-mist sm:grid sm:min-h-[4.75rem] sm:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)_10rem_1.25rem] sm:items-center sm:gap-x-6"
      >
        <span className="flex min-w-0 items-baseline justify-between gap-4 sm:contents">
          <span className="min-w-0 truncate font-medium text-navy">{personLabel(participant)}</span>
          <time dateTime={participant.created_at} title={addedExact} className="shrink-0 text-sm text-slate tabular-nums sm:hidden">
            <span className="sr-only">Added </span>
            {added}
          </time>
        </span>
        <span className="min-w-0 truncate text-sm">
          <DisplayLabel label={participant.reference_code ? participant.display_label : null} />
        </span>
        <time
          dateTime={participant.created_at}
          title={addedExact}
          className="hidden text-sm text-navy tabular-nums sm:block"
        >
          <span className="sr-only">Added </span>
          {added}
        </time>
        <ChevronRight size={18} aria-hidden="true" className="hidden text-slate sm:block" />
      </Link>
    </li>
  );
}

function previousPage(page: number, totalPages: number): number {
  if (page > totalPages) return totalPages;
  return Math.max(1, page - 1);
}

function resultCount(total: number, query: string, people: string, person: string): string {
  const count = total.toLocaleString();
  if (query.length > 0) {
    return `${count} ${total === 1 ? "match" : "matches"} for “${query}”`;
  }
  return `${count} ${total === 1 ? person : people}`;
}

export function ParticipantDirectoryPage() {
  const { me, expireSession } = useAuth();
  const words = WORKFLOW_WORDS[activeContext(me?.membership)];
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedQuery = searchParams.get("q")?.trim() ?? "";
  const sortParam = searchParams.get("sort");
  const sort: ParticipantSort = isSort(sortParam) ? sortParam : DEFAULT_SORT;
  const page = parsePage(searchParams.get("page"));
  const [queryDraft, setQueryDraft] = useState(appliedQuery);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const draftRef = useRef(queryDraft);
  const searchId = useId();
  const sortId = useId();
  const searchHintId = useId();
  draftRef.current = queryDraft;
  useDocumentTitle(words.peopleTitle);

  useEffect(() => {
    if (draftRef.current.trim() !== appliedQuery) setQueryDraft(appliedQuery);
  }, [appliedQuery]);

  useEffect(() => {
    const trimmed = queryDraft.trim();
    if (trimmed === appliedQuery) return;
    const timer = window.setTimeout(() => {
      setSearchParams((current) => writeParams(current, { q: trimmed, page: 1 }), { replace: true });
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [queryDraft, appliedQuery, setSearchParams]);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    getParticipants(
      {
        q: appliedQuery,
        sort,
        page,
        page_size: PAGE_SIZE,
      },
      controller.signal,
    )
      .then((payload: unknown) => {
        if (controller.signal.aborted) return;
        const list = readParticipantList(payload);
        if (list === null) {
          throw new ApiError(500, "internal_error", "The server returned an unexpected response.");
        }
        setState({ status: "ready", list });
      })
      .catch((error: unknown) => {
        if (isAbortError(error) || controller.signal.aborted) return;
        if (isUnauthorized(error)) {
          expireSession();
          return;
        }
        setState({ status: "error", error });
      });
    return () => controller.abort();
  }, [appliedQuery, sort, page, reloadKey, expireSession]);

  function onSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = queryDraft.trim();
    setSearchParams((current) => writeParams(current, { q: trimmed, page: 1 }), { replace: true });
  }

  function clearSearch() {
    setQueryDraft("");
    setSearchParams((current) => writeParams(current, { q: "", page: 1 }), { replace: true });
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 lg:px-10 lg:py-12">
      <PageHeader
        title={words.peopleTitle}
        description={words.directoryDescription}
        actions={<AddParticipantLink label={words.add} />}
      />

      <div className="mt-10 rounded-lg bg-mist px-6 py-6">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end">
          <search className="min-w-0 flex-1">
            <form onSubmit={onSearchSubmit} className="flex flex-col gap-1.5">
              <label htmlFor={searchId} className="text-sm font-medium text-navy">
                Search
              </label>
              <div className="relative">
                <Search
                  size={16}
                  aria-hidden="true"
                  className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate"
                />
                <input
                  id={searchId}
                  type="text"
                  role="searchbox"
                  name="q"
                  value={queryDraft}
                  maxLength={80}
                  autoComplete="off"
                  spellCheck={false}
                  enterKeyHint="search"
                  placeholder={words.searchPlaceholder}
                  aria-describedby={searchHintId}
                  onChange={(event) => setQueryDraft(event.target.value)}
                  className={`${CONTROL} h-10 pr-10 pl-9`}
                />
                {queryDraft.length > 0 ? (
                  <button
                    type="button"
                    aria-label="Clear search"
                    onClick={clearSearch}
                    className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-md text-slate transition-colors duration-150 hover:text-navy"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                ) : null}
              </div>
              <p id={searchHintId} className="text-xs text-slate">
                Searches the full directory, not only this page.
              </p>
            </form>
          </search>

          <div className="flex w-full flex-col gap-1.5 lg:w-64">
            <label htmlFor={sortId} className="text-sm font-medium text-navy">
              Sort
            </label>
            <div className="relative">
              <select
                id={sortId}
                value={sort}
                onChange={(event) => {
                  const next = event.target.value;
                  if (!isSort(next)) return;
                  setSearchParams((current) => writeParams(current, { sort: next, page: 1 }), { replace: true });
                }}
                className={`${CONTROL} h-10 appearance-none pr-10 pl-3`}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <ChevronDown
                size={18}
                aria-hidden="true"
                className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-slate"
              />
            </div>
          </div>
        </div>
      </div>

      {state.status === "loading" ? <DirectorySkeleton label={`Loading ${words.people}`} /> : null}

      {state.status === "error" ? (
        <Alert
          variant="error"
          title={`Couldn't load ${words.people}`}
          className="mt-10"
          action={
            <Button variant="secondary" size="sm" onClick={() => setReloadKey((key) => key + 1)}>
              <RotateCw size={14} aria-hidden="true" />
              Retry
            </Button>
          }
        >
          {getErrorMessage(state.error)}
        </Alert>
      ) : null}

      {state.status === "ready" && state.list.total === 0 && appliedQuery.length === 0 ? (
        <div className="mt-10 animate-fade-in">
          <EmptyState
            icon={Users}
            title={words.emptyTitle}
            description={words.emptyDescription}
            action={<AddParticipantLink label={words.add} size="sm" />}
          />
        </div>
      ) : null}

      {state.status === "ready" && state.list.total === 0 && appliedQuery.length > 0 ? (
        <div className="mt-10 animate-fade-in">
          <EmptyState
            icon={Search}
            title={words.noMatchTitle}
            description={`Nothing in this workspace matches “${appliedQuery}”. The search covers the full directory.`}
            action={
              <Button variant="secondary" size="sm" onClick={clearSearch}>
                Clear search
              </Button>
            }
          />
        </div>
      ) : null}

      {state.status === "ready" && state.list.total > 0 ? (
        <DirectoryResults
          list={state.list}
          query={appliedQuery}
          person={words.person}
          people={words.people}
          onPage={(nextPage) => {
            setSearchParams((current) => writeParams(current, { page: nextPage }), { replace: false });
          }}
        />
      ) : null}
    </div>
  );
}

function DirectoryResults({
  list,
  query,
  person,
  people,
  onPage,
}: {
  list: ParticipantList;
  query: string;
  person: string;
  people: string;
  onPage: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(list.total / list.page_size));
  const rangeStart = list.items.length === 0 ? 0 : (list.page - 1) * list.page_size + 1;
  const rangeEnd = list.items.length === 0 ? 0 : rangeStart + list.items.length - 1;

  return (
    <div className="mt-10 flex animate-fade-in flex-col gap-6">
      <p className="text-sm text-slate" aria-live="polite">
        {resultCount(list.total, query, people, person)}
      </p>

      <div className="overflow-hidden rounded-lg border border-border">
        <div className="hidden border-b border-border px-6 py-4 text-xs font-medium text-slate sm:grid sm:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)_10rem_1.25rem] sm:gap-x-6">
          <span>Identifier</span>
          <span>Label</span>
          <span>Added</span>
          <span className="sr-only">Open</span>
        </div>
        {list.items.length === 0 ? (
          <p className="px-6 py-8 text-sm text-slate">No records on this page.</p>
        ) : (
          <ul aria-label={people}>
            {list.items.map((participant) => (
              <ParticipantRow key={participant.id} participant={participant} />
            ))}
          </ul>
        )}
      </div>

      {totalPages > 1 || list.items.length === 0 ? (
        <nav aria-label="Pagination" className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          {list.items.length > 0 ? (
            <p className="text-sm text-slate tabular-nums">
              Showing {rangeStart.toLocaleString()}–{rangeEnd.toLocaleString()} of {list.total.toLocaleString()}
            </p>
          ) : null}
          <div className="flex items-center gap-3 sm:ml-auto">
            <Button
              variant="secondary"
              size="sm"
              disabled={list.page <= 1}
              onClick={() => onPage(previousPage(list.page, totalPages))}
            >
              Previous
            </Button>
            <span className="text-sm text-slate tabular-nums">
              Page {list.page.toLocaleString()} of {totalPages.toLocaleString()}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={list.page >= totalPages}
              onClick={() => onPage(list.page + 1)}
            >
              Next
            </Button>
          </div>
        </nav>
      ) : (
        <p className="text-sm text-slate tabular-nums">
          Showing {rangeStart.toLocaleString()}–{rangeEnd.toLocaleString()} of {list.total.toLocaleString()}
        </p>
      )}
    </div>
  );
}
