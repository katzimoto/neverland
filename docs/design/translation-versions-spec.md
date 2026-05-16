# Translation Versions UX Spec

## Purpose

Translation versions let users request translations manually, keep every
generated translation as a selectable version, and choose which version they
want to read in document preview.

This builds on Phase 05 translation enrichment. The design here expands the UI
and contract from a single `translation_quality` label into a versioned reading
experience.

## Definition

In this spec, manual translation means a user-initiated translation request. It
does not mean user-authored translation editing in the MVP.

Every document can have:

- Original source content.
- Fast machine translation from ingestion.
- One or more high-quality/manual translation versions.
- Pending or failed translation versions.

## User Goals

- Request a better translation when the current preview is poor or missing.
- Keep reading the current version while the new translation runs.
- See which translation version is currently displayed.
- Switch between original, fast, and manual/high-quality versions.
- Understand who requested a translation and when it was created.
- Return to a preferred version without confusion.

## Non-Goals

- No side-by-side diff in the MVP.
- No collaborative editing of translated text in the MVP.
- No per-paragraph translation voting in the MVP.
- No automatic translation to languages the user cannot read unless explicitly
  requested by config or user action.

## Placement In The UI

### Document Toolbar

Add a translation version selector near the document title/source metadata.

Recommended toolbar order:

1. Back to search.
2. Document title and source metadata.
3. Translation version selector.
4. Request translation.
5. Download.
6. More menu.

Selector label examples:

- `Original`
- `Fast translation`
- `High quality v1`
- `Manual v2`
- `Manual v3 pending`

The selector is a combobox/menu, not a segmented control, because the version
list can grow.

### Version Menu

The version menu shows:

- Version label.
- Language pair.
- Status.
- Requested by.
- Completed or requested time.
- Quality/source indicator.

Example:

```text
Translation
Current: High quality v2

Original                English
Fast translation        English to Hebrew   Available
High quality v1         English to Hebrew   Apr 20
High quality v2         English to Hebrew   Apr 27   Current
Manual v3               English to Hebrew   Pending
```

Pending versions are visible but not selectable as preview content. Selecting a
pending item opens its status details.

Failed versions are visible in the menu for users who requested them and admins.
They show a retry action when the user has permission.

### Request Translation Dialog

Open from `Request translation`.

Fields:

- Source language, read-only when detected with high confidence.
- Target language.
- Quality: high quality, default.
- Optional note, visible only in version metadata and audit surfaces.

Dialog copy:

- Title: `Request translation`
- Body: `A new translation version will be created. You can keep reading while
  it runs.`
- Submit: `Request translation`
- Cancel: `Cancel`

After submit:

- Keep the current preview version selected.
- Add a pending version to the selector.
- Show toast: `Translation requested.`
- If the same language pair is already pending, show:
  `Translation already queued.`

### Reading A Version

When a user selects a version:

- The preview re-renders without leaving the document route.
- The toolbar clearly shows the selected version.
- The details tab shows version metadata.
- The preview should preserve scroll position by anchor when possible.
- If anchor preservation is unavailable, keep the user near the same relative
  scroll position.
- Search-in-document operates within the selected version.
- Copy selected text copies from the selected version.

Deep links:

- Support `?translation_version=<version_id>` for shareable links when the
  backend can authorize that version.
- Invalid or inaccessible version IDs fall back to the default version and show
  a small warning.

### Default Version Selection

Default selection should feel helpful but predictable:

1. Use the version specified in the URL if valid.
2. Use the user's last selected version for the document when available.
3. Use the newest available high-quality version matching the user's preferred
   language.
4. Use fast translation when high quality is unavailable.
5. Use original content.

Do not auto-switch a reader from their current selected version when a pending
translation completes. Instead, show a toast:

`A new translation version is ready.`

The toast action is:

`View`

## Version Labels

Use human labels in the UI, not raw IDs.

Recommended labels:

- `Original`
- `Fast translation`
- `High quality v1`
- `Manual v2`
- `Manual v3 pending`
- `Manual v3 failed`

Version details show exact metadata:

- Source language.
- Target language.
- Translation provider or worker.
- Requested by.
- Requested time.
- Completed time.
- Status.
- Error summary, when failed.

## Status States

Available:

- Version can be selected.
- Preview can render it.

Pending:

- Version exists but content is not ready.
- Show progress copy: `Translation is queued.`

Running:

- Worker has started.
- Show progress copy: `Translation is running.`

Failed:

- Show copy: `Translation failed. Original content is still available.`
- Preserve retry when allowed.

Canceled:

- Only admins see canceled versions in queue/audit surfaces.
- Normal users do not need canceled versions in the selector.

## Permissions

Viewing:

- Any user who can view the document can view available translation versions
  for that document.
- Version metadata must not reveal inaccessible document details because it is
  scoped to the current document.

Requesting:

- Any user with document access can request a translation unless the feature is
  disabled by config.
- Admins can retry failed versions and inspect queue details.

Deleting:

- No user-facing delete for translation versions in the MVP.
- Admin retention management belongs in admin operations or storage policy.

## Empty And Error States

No translations:

- Selector shows `Original`.
- Request action remains available when allowed.

Translation unavailable:

- Copy: `Translation is unavailable. Showing original content.`
- Keep request translation action available when allowed.

Version unavailable:

- Copy: `This translation version is not available. Showing original content.`

Request failure:

- Preserve dialog fields.
- Copy: `Translation was not requested. Try again.`

Queue disabled:

- Hide request action or show disabled tooltip:
  `Translation requests are disabled.`

## Accessibility

- The version selector is keyboard reachable and named `Translation version`.
- Pending and failed states are announced when the menu opens.
- Toasts for ready/failed versions use polite live regions.
- Language names are readable text, not flag-only icons.
- The request dialog traps focus and returns focus to the trigger on close.
- Selecting a version announces the new version label.

## Data Contracts Needed From Backend

Translation version:

```ts
type TranslationVersion = {
  translation_version_id: string;
  document_id: string;
  version_number: number;
  label: string;
  source_language: string | null;
  target_language: string;
  quality: "fast" | "high";
  request_type: "ingestion" | "manual" | "auto_enrich";
  status: "available" | "pending" | "running" | "failed" | "canceled";
  provider: string | null;
  requested_by_id: string | null;
  requested_by_display_name: string | null;
  requested_at: string;
  completed_at: string | null;
  error_summary: string | null;
  can_retry: boolean;
};
```

Version list response:

```ts
type TranslationVersionsResponse = {
  document_id: string;
  original_language: string | null;
  default_translation_version_id: string | null;
  selected_translation_version_id: string | null;
  versions: TranslationVersion[];
  can_request_translation: boolean;
};
```

Create request:

```ts
type CreateTranslationRequest = {
  target_language: string;
  source_language?: string;
  note?: string;
};
```

Preview request:

```text
GET /documents/{document_id}/preview?translation_version_id={translation_version_id}
```

Suggested endpoints:

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/documents/{document_id}/translation-versions` | Document access | List versions |
| POST | `/documents/{document_id}/translation-versions` | Document access | Request manual translation |
| POST | `/documents/{document_id}/translation-versions/{version_id}/retry` | Admin or requester when allowed | Retry failed version |
| GET | `/documents/{document_id}/preview?translation_version_id=...` | Document access | Render selected version |

## Implementation Notes For Existing Phase 05

The existing `translation_quality` field remains useful as a summary, but the
UI should prefer version metadata when available.

Recommended compatibility mapping:

| Existing State | Version UI |
|---|---|
| `null` | Original only, request available |
| `fast` | Fast translation available |
| `pending_high` | Pending manual/high-quality version |
| `high` | At least one high-quality version available |

## Acceptance Checklist

- Users can request a manual translation from document preview.
- The current preview does not disappear while a translation is pending.
- Every created translation appears as a version with status.
- Users can choose original, fast, and available high-quality/manual versions.
- Pending and failed versions are understandable but do not block reading.
- The selected version is visible in the toolbar.
- Version choice survives preview refresh for the current document.
- Deep links to versions work when authorized.
- Search-in-document and copy selection use the selected version.
- Translation request failures preserve user input.
