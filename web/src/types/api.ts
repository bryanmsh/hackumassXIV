/**
 * Contract 1 (HTTP API) types for the Mirai web app.
 *
 * ⚠️ PROVISIONAL. These shapes follow the frozen Contract 1 route table and the
 * Contract 2 Pydantic models in "Product and technical spec.md", but the exact
 * JSON (field names, nesting, error bodies) has NOT yet been agreed with Andrew.
 * Every guess that the spec does not pin down is marked `PROVISIONAL:` below.
 * When the agreed example file lands, update this file first; the client,
 * mocks and screens all type-check against it.
 *
 * Coordinates: every position crossing HTTP is a fraction in [0, 1] of the
 * original page, origin top-left, x across, y down (FINAL build plan). The API
 * converts to master pixels once; the browser never does.
 */

// ---------- Shared primitives ----------

/** Fractional point [x, y], each in [0, 1]. PROVISIONAL: array vs {x, y}. */
export type NormPoint = [x: number, y: number];

/** Fractional box [x0, y0, x1, y1], each in [0, 1], x0 < x1, y0 < y1. */
export type NormBox = [x0: number, y0: number, x1: number, y1: number];

/** Display look. The app shows names (see utils/display.ts); the API takes numbers. */
export type Level = 1 | 2 | 3 | 4;

/** Uppercase/lowercase hex color, e.g. "#E53935". */
export type HexColor = string;

// ---------- Books and pages ----------

export type BookState = 'ingesting' | 'ready' | 'failed';

/** PROVISIONAL: lowercase snake_case, matching Contract 2 PageResult.state plus "processing". */
export type PageState =
  | 'processing'
  | 'ready'
  | 'needs_subject'
  | 'no_clear_subject'
  | 'failed'
  | 'unsupported';

export type PageKind = 'single' | 'several' | 'scene';

export type CandidateSource = 'auto' | 'click' | 'manual';

/** Known page flags from rasterize(); the server may add more. */
export type PageFlag = 'spread' | 'low_quality' | (string & {});

export interface Credits {
  author: string | null;
  illustrator: string | null;
  publisher: string | null;
  source: string | null;
  license: string | null;
}

/**
 * Contract 2 Candidate, minus mask_path (a server filesystem path that must
 * never be exposed). `box` is NORMALIZED here, unlike the Python model.
 */
export interface Candidate {
  label: string;
  synonyms: string[];
  box: NormBox;
  confidence: number;
  mask_hash: string;
  source: CandidateSource;
}

export type SecondLookStatus = 'pass' | 'warn' | 'pending';

export interface SecondLook {
  status: SecondLookStatus;
  answer: string | null;
  detail: string | null;
}

export interface Page {
  id: string;
  book_id: string;
  number: number;
  state: PageState;
  reason: string | null;
  flags: PageFlag[];
  page_kind: PageKind | null;
  candidates: Candidate[];
  /** PROVISIONAL: index into `candidates`, as in Contract 2 PageResult.selected. */
  selected: number | null;
  subject_hash: string | null;
  confirmed: boolean;
  omitted: boolean;
  second_look: SecondLook | null;
  /** Page text from the PDF text layer, when present. PROVISIONAL: may be omitted. */
  text?: string | null;
}

export interface Book {
  id: string;
  title: string;
  credits: Credits;
  state: BookState;
  page_count: number | null;
  created_at: string;
  pages: Page[];
}

/** POST /books returns the id at once, with the book ingesting. */
export interface UploadBookResponse {
  book_id: string;
  state: BookState;
}

export interface UploadBookInput {
  file: File;
  title?: string;
  credits?: Partial<Credits>;
}

export interface UpdateBookInput {
  title?: string;
  credits?: Partial<Credits>;
}

// ---------- Subject selection ----------

/** POST /pages/{id}/subject — exactly one shape per request. */
export type SubjectRequest =
  | { candidate: number }
  | { point: NormPoint }
  | { label: string; outline: NormPoint[] };
// P1 only, not before checkpoint 2: | { refine_point: NormPoint }

export interface RetryInput {
  force?: boolean;
}

// ---------- Profiles ----------

export type SubjectSize = 'small' | 'medium' | 'large';
export type SubjectPosition = 'center' | 'left' | 'right' | 'upper' | 'lower';
export type TextMode = 'off' | 'below';
export type OutlineMode = 'off' | 'thin' | 'thick';

/** Contract 2 Settings. size/position/text_mode/outline have P1 controls only. */
export interface Settings {
  colors: HexColor[];
  background: HexColor;
  size: SubjectSize;
  position: SubjectPosition;
  text_mode: TextMode;
  outline: OutlineMode;
}

export interface Profile {
  id: string;
  name: string;
  level: Level;
  settings: Settings;
  settings_hash: string;
  contrast_override_note: string | null;
}

export interface ProfileInput {
  name: string;
  level: Level;
  settings: Settings;
  contrast_override_note: string | null;
}

export type ProfilePatch = Partial<ProfileInput>;

export interface PreviewInput {
  page_id: string;
  settings: Settings;
  level: Level;
}

/** Query for a saved, versioned image (render or reader page). */
export interface VersionQuery {
  profile: string;
  level: Level;
  v: string;
}

export interface SheetQuery {
  profile: string;
  level: Level;
}

// ---------- Checks and contact sheet ----------

export type CheckStatus = 'pass' | 'warn' | 'fail';

export interface CheckItem {
  status: CheckStatus;
  value: number | null;
  detail: string;
}

export interface CheckResult {
  fidelity: CheckItem;
  page_edge: CheckItem;
  /** Null at Outlined (level 4), where the background is not checked. */
  background: CheckItem | null;
  contrast: CheckItem;
  size: CheckItem;
  /** Only when text is shown. PROVISIONAL: null vs omitted. */
  text_contrast: CheckItem | null;
}

/** PROVISIONAL representation of the current approval state of one page version. */
export type ApprovalState = 'approved' | 'rejected' | 'none';

export interface SheetPage {
  page_id: string;
  number: number;
  /** Exact version token `v` from the server. Echo back unchanged; never derive. Null when no confirmed subject. */
  version: string | null;
  state: PageState;
  confirmed: boolean;
  omitted: boolean;
  label: string | null;
  /** "manual" pages are shown as "outlined by teacher". */
  source: CandidateSource | null;
  checks: CheckResult | null;
  second_look: SecondLook | null;
  approval: ApprovalState;
  /** Server-built /api/render URL. The app fetches via api.getRender instead. */
  preview_url: string | null;
}

export interface Sheet {
  book_id: string;
  profile_id: string;
  level: Level;
  pages: SheetPage[];
}

export type Decision = 'approve' | 'reject';

export interface ApproveRequest {
  profile_id: string;
  level: Level;
  pages: { page_id: string; version: string; decision: Decision }[];
}

export interface ApprovalRecord {
  page_id: string;
  profile_id: string;
  level: Level;
  version: string;
  decision: Decision;
  at: string;
}

/** PROVISIONAL 409 body: matching pages are recorded, changed pages are not. */
export interface ApproveConflictBody {
  detail: string;
  changed: { page_id: string; sent: string; current: string | null }[];
  recorded: ApprovalRecord[];
}

export interface ApproveSuccessBody {
  approvals: ApprovalRecord[];
}

export type ApproveOutcome =
  | { ok: true; approvals: ApprovalRecord[] }
  | { ok: false; conflict: ApproveConflictBody };

// ---------- Reader ----------

export interface ReaderPage {
  page_id: string;
  number: number;
  /** Approval token for this exact version; pass to GET /reader/page. */
  v: string;
  /** Server-built /api/reader/page URL. The app rebuilds it via api.getReaderPage. */
  image_url: string;
}

/** PROVISIONAL reasons. */
export type SkipReason = 'omitted' | 'rejected' | 'not_approved';

export interface SkippedPage {
  page_id: string;
  number: number;
  reason: SkipReason;
}

export interface ReaderVersion {
  profile_id: string;
  profile_name: string;
  level: Level;
  fully_approved: boolean;
}

export interface ReaderManifest {
  book_id: string;
  title: string;
  profile_id: string;
  level: Level;
  pages: ReaderPage[];
  skipped: SkippedPage[];
  credits: Credits;
  /** PROVISIONAL: adaptation notice text for the credits screen. */
  adaptation_note: string;
  versions: ReaderVersion[];
}

// ---------- Evaluation (P1) ----------

export interface EvalSummary {
  pages: number;
  correct_subjects: number;
  correctly_flagged: number;
  confidently_wrong: number;
  cutout_defects: number;
  seconds_per_page: number | null;
}

// ---------- Errors ----------

/** FastAPI-style error body. `detail` may be a string or validation list. */
export interface ErrorBody {
  detail?: string | { msg?: string; loc?: (string | number)[] }[] | Record<string, unknown>;
}
