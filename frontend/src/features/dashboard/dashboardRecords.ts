import { ApiError, getParticipants, isAbortError } from "../../lib/api";
import type { DashboardSummary } from "../../lib/types";

/** Rows shown on the overview. The participants request asks for this many, newest first. */
const RECENT_LIMIT = 5;

export type DashboardRecord = {
  id: string;
  label: string;
  detail: string | null;
  occurredAt: string | null;
  href: string | null;
};

export type EmbeddedRecords =
  | { kind: "absent" }
  | { kind: "unreadable" }
  | { kind: "records"; records: DashboardRecord[] };

export type PresentedRecords =
  | { status: "empty" }
  | { status: "ready"; records: DashboardRecord[]; totalReturned: number; sortedByDate: boolean };

export type ParticipantListResult = { status: "unavailable" } | PresentedRecords;

const STATUS_KEYS = ["status"] as const;
const TIME_KEYS = ["occurred_at", "created_at", "enrolled_at", "completed_at", "updated_at"] as const;
const ASSESSMENT_LABEL_KEYS = ["title", "label", "modality", "protocol_name", "protocol"] as const;
const ASSESSMENT_DETAIL_KEYS = ["participant_code", "reference_code", "participant", "code"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readString(record: Record<string, unknown>, keys: readonly string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed.length > 0) return trimmed;
  }
  return null;
}

function readId(record: Record<string, unknown>): string | null {
  const id = record.id;
  if (typeof id === "string" && id.trim().length > 0) return id.trim();
  if (typeof id === "number" && Number.isFinite(id)) return String(id);
  return null;
}

function parseRecord(
  value: unknown,
  labelKeys: readonly string[],
  detailKeys: readonly string[],
): DashboardRecord | null {
  if (!isRecord(value)) return null;
  const id = readId(value);
  if (id === null) return null;
  const label = readString(value, labelKeys);
  if (label === null) return null;
  const detailParts = [readString(value, detailKeys), readString(value, STATUS_KEYS)].filter(
    (part): part is string => part !== null && part !== label,
  );
  return {
    id,
    label,
    detail: detailParts.length > 0 ? detailParts.join(" · ") : null,
    occurredAt: readString(value, TIME_KEYS),
    href: null,
  };
}

/** Matches a person record: code when one exists, otherwise the label, plus created time. */
function parseParticipant(value: unknown): DashboardRecord | null {
  if (!isRecord(value)) return null;
  const id = readId(value);
  const referenceCode = readString(value, ["reference_code"]);
  const createdAt = readString(value, ["created_at"]);
  const displayLabel = value.display_label;
  if (id === null || createdAt === null) return null;
  if (displayLabel !== null && displayLabel !== undefined && typeof displayLabel !== "string") return null;
  const labelText = typeof displayLabel === "string" ? displayLabel.trim() : "";
  if (referenceCode === null && labelText.length === 0) return null;
  return {
    id,
    label: referenceCode ?? labelText,
    detail: referenceCode !== null && labelText.length > 0 && labelText !== referenceCode ? labelText : null,
    occurredAt: createdAt,
    href: `/app/participants/${encodeURIComponent(id)}`,
  };
}

function parseParticipantList(value: unknown[]): DashboardRecord[] | "unreadable" {
  const records: DashboardRecord[] = [];
  for (const item of value) {
    const record = parseParticipant(item);
    if (record === null) return "unreadable";
    records.push(record);
  }
  return records;
}

export function readRecentParticipants(summary: DashboardSummary): EmbeddedRecords {
  if (!("recent_participants" in summary)) return { kind: "absent" };
  const value = (summary as DashboardSummary & Record<string, unknown>).recent_participants;
  if (value === null || value === undefined) return { kind: "absent" };
  if (!Array.isArray(value)) return { kind: "unreadable" };
  const parsed = parseParticipantList(value);
  if (parsed === "unreadable") return { kind: "unreadable" };
  return { kind: "records", records: parsed };
}

export function readRecentAssessments(summary: DashboardSummary): EmbeddedRecords {
  if (!("recent_assessments" in summary)) return { kind: "absent" };
  const value = (summary as DashboardSummary & Record<string, unknown>).recent_assessments;
  if (value === null || value === undefined) return { kind: "absent" };
  if (!Array.isArray(value)) return { kind: "unreadable" };
  const records: DashboardRecord[] = [];
  for (const item of value) {
    const record = parseRecord(item, ASSESSMENT_LABEL_KEYS, ASSESSMENT_DETAIL_KEYS);
    if (record === null) return { kind: "unreadable" };
    records.push(record);
  }
  return { kind: "records", records };
}

function timeValue(iso: string | null): number | null {
  if (iso === null) return null;
  const value = Date.parse(iso);
  return Number.isNaN(value) ? null : value;
}

export function presentRecords(records: DashboardRecord[]): PresentedRecords {
  if (records.length === 0) return { status: "empty" };
  const times = records.map((record) => timeValue(record.occurredAt));
  const sortedByDate = times.every((value) => value !== null);
  const ordered = sortedByDate
    ? records
        .map((record, index) => ({ record, time: times[index] ?? 0 }))
        .sort((a, b) => b.time - a.time)
        .map((entry) => entry.record)
    : records;
  return {
    status: "ready",
    records: ordered.slice(0, RECENT_LIMIT),
    totalReturned: ordered.length,
    sortedByDate,
  };
}

function readParticipantItems(body: unknown): DashboardRecord[] {
  if (!isRecord(body) || !Array.isArray(body.items)) {
    throw new ApiError(200, "unexpected_response", "The participant list could not be read.");
  }
  const parsed = parseParticipantList(body.items);
  if (parsed === "unreadable") {
    throw new ApiError(200, "unexpected_response", "The participant list could not be read.");
  }
  return parsed;
}

/**
 * Newest participants, when the summary does not include them.
 * A 404 means this server has no participant list. The workspace count still comes only from the summary metric.
 */
export async function fetchParticipants(signal: AbortSignal): Promise<ParticipantListResult> {
  try {
    const body = await getParticipants({ sort: "-created_at", page: 1, page_size: RECENT_LIMIT }, signal);
    return presentRecords(readParticipantItems(body));
  } catch (error) {
    if (isAbortError(error)) throw error;
    if (error instanceof ApiError && error.status === 404) return { status: "unavailable" };
    throw error;
  }
}
