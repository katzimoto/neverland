# Document Comments UX Spec

## Purpose

Document comments let users discuss a document without anchoring every note to
a selected text range. They are visible to everyone who can access the document,
and they should feel like a lightweight discussion thread inside the document
preview.

This is separate from annotations:

- Comments are document-level and shared by default.
- Annotations are anchored to text, regions, table cells, or other preview
  positions.

## User Goals

- Add a short note, long explanation, or emoji-only comment quickly.
- Read the document discussion without losing preview context.
- Edit or delete my own comments.
- Let admins correct or remove comments when required.
- Understand when a comment was edited or deleted.

## Non-Goals

- No private comments in this feature. Private notes remain part of
  annotations.
- No threaded replies in the MVP.
- No file attachments in comments.
- No rich text editor in the MVP.
- No emoji reactions in the MVP. Users can still write emoji in the comment
  body.

## Visibility And Permissions

Visibility:

- A comment is visible to every user who can view the document.
- A comment is never visible to users who do not have document access.
- Search results, Q&A, notifications, and activity surfaces must not reveal
  comments from inaccessible documents.

Author permissions:

- The creator can edit or delete their own comment.
- The creator can edit the full body, including long text and emoji.
- The creator cannot transfer ownership.

Admin permissions:

- Admins can edit or delete any comment.
- Admin edits show an `edited by admin` indicator.
- Admin deletes are audit logged.

System behavior:

- Comment visibility follows document permissions at read time.
- If a user loses document access, they lose access to comments on that
  document, including comments they created earlier.
- Deleted comments are hidden from the normal user thread.
- Admin/audit surfaces may retain deleted comment metadata according to the
  audit policy.

## Placement In The UI

### Document Preview

Add a `Comments` tab to the right insight pane on `/doc/:documant_id`.

Recommended tab order:

1. Summary
2. Details
3. Comments
4. Annotations
5. Related

The `Comments` tab label includes a count badge when count is available:

- `Comments`
- `Comments 3`

The tab content uses a single-column thread:

```text
+------------------------------------------------+
| Comments 3                              Sort v |
|------------------------------------------------|
| Add a comment...                               |
| [ multiline composer                         ] |
| [Cancel]                         [Comment]     |
|------------------------------------------------|
| Mira Chen                         2 min ago    |
| This contract has a renewal clause on page 4.  |
| [Edit] [Delete]                               |
|------------------------------------------------|
| Arun Patel                     edited 1h ago   |
| [emoji] Looks aligned with the Jira ticket.    |
+------------------------------------------------+
```

### Composer

The composer should feel immediate but not cramped:

- Placeholder: `Add a comment`
- Supports plain text, line breaks, and Unicode emoji.
- No product-level short character limit.
- Long-form comments are supported without a visible character counter.
- Draft text is preserved while switching tabs or preview versions.
- Submit is disabled when the trimmed body is empty.
- `Cmd/Ctrl+Enter` submits.
- `Esc` cancels only when the editor is focused and unchanged, or after a
  confirmation when there are unsaved changes.

The backend may enforce infrastructure safety limits, but the UI should not
impose an artificial short limit. If the API rejects an oversized comment, keep
the draft in place and show a calm inline error.

### Comment Item

Each comment item shows:

- Author display name.
- Optional admin badge when the author is an admin.
- Created time.
- Edited indicator when applicable.
- Body text with preserved line breaks.
- Author/admin actions where permitted.

Long comment display:

- Show the first 12 lines in the thread.
- Provide `Show more` and `Show less`.
- Full content can also open in a detail dialog from the more menu.
- Editing always opens the full content.

Emoji-only comment display:

- Render emoji-only comments slightly larger than normal text, but within the
  same comment item layout.
- Do not animate emoji.

### Sorting

Default sort: newest first.

Sort options:

- Newest first.
- Oldest first.

Changing sort must not clear drafts or reset the preview scroll position.

### Empty State

When there are no comments:

- Title: `No comments yet`
- Body: `Start a document discussion that everyone with access can see.`
- Primary action focuses the composer.

When the user can view comments but cannot create one:

- Title: `Comments are read-only`
- Body: `You can read comments on this document, but you cannot add one.`

## Edit Flow

Editing happens inline by default:

1. User chooses `Edit`.
2. The comment body becomes a multiline editor.
3. Actions become `Cancel` and `Save`.
4. Save updates the item in place.
5. The item shows `edited` with updated timestamp.

Admin edit copy:

- Save confirmation is not required for normal edits.
- When an admin edits someone else's comment, show a compact note:
  `Editing as admin`.
- The saved item shows `edited by admin`.

Unsaved changes:

- Navigating away with an unsaved edit prompts confirmation.
- Failed saves preserve the edited draft.

## Delete Flow

Deleting requires confirmation:

- Title: `Delete comment?`
- Body for own comment: `This removes the comment from the document discussion.`
- Body for admin delete: `This removes the comment for everyone and records an
  admin action.`
- Primary action: `Delete`
- Secondary action: `Cancel`

After delete:

- Remove the item from the visible thread.
- Show toast: `Comment deleted.`
- Do not show an undo action unless the backend supports restore.

## Loading And Error States

Loading:

- Use skeleton comment rows that match the final layout.
- The composer can render while comments load if permissions are already known.

Create failure:

- Preserve the draft.
- Copy: `Comment was not posted. Try again.`

Edit failure:

- Preserve the draft.
- Copy: `Comment was not updated. Try again.`

Delete failure:

- Keep the item visible.
- Copy: `Comment was not deleted. Try again.`

Permission failure:

- Copy: `You no longer have access to comment on this document.`
- Refresh document permission state.

## Accessibility

- The comments tab is reachable by keyboard.
- The composer has a visible label, not placeholder-only naming.
- Submit, edit, delete, and sort controls have accessible names.
- New comments are announced in a polite live region.
- Failed create/edit/delete operations are announced.
- Long comments preserve readable line length.
- Focus returns to the triggering action after closing edit/delete dialogs.

## Activity And Notifications

MVP behavior:

- Comment creation appears in the creator's activity history.
- Admin edits/deletes appear in audit logs.
- The app shell notification count does not increment for every document
  comment unless subscriptions later opt into comment activity.

Later behavior:

- A user may subscribe to comment activity on a document.
- Mentions may create notifications if mentions are added in a future phase.

## Data Contracts Needed From Backend

Comment:

```ts
type DocumentComment = {
  comment_id: string;
  documant_id: string;
  author_id: string;
  author_display_name: string;
  author_is_admin: boolean;
  body: string;
  created_at: string;
  updated_at: string;
  edited_at: string | null;
  edited_by_id: string | null;
  edited_by_display_name: string | null;
  edited_by_admin: boolean;
  deleted_at: string | null;
  can_edit: boolean;
  can_delete: boolean;
};
```

List response:

```ts
type DocumentCommentsResponse = {
  documant_id: string;
  comments: DocumentComment[];
  total_count: number;
  can_comment: boolean;
};
```

Create request:

```ts
type CreateDocumentCommentRequest = {
  body: string;
};
```

Update request:

```ts
type UpdateDocumentCommentRequest = {
  body: string;
};
```

Suggested endpoints:

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/documents/{documant_id}/comments` | Document access | List visible comments |
| POST | `/documents/{documant_id}/comments` | Document access | Create a comment |
| PATCH | `/documents/{documant_id}/comments/{comment_id}` | Creator or admin | Edit comment body |
| DELETE | `/documents/{documant_id}/comments/{comment_id}` | Creator or admin | Delete comment |

## Acceptance Checklist

- Comments are visible to all users with document access.
- Comments are not visible to users without document access.
- Users can create word-only, emoji-only, short, and long comments.
- Long comments are readable without taking over the preview pane.
- Creators can edit and delete their own comments.
- Admins can edit and delete any comment.
- Admin edits/deletes are distinguishable and audit-ready.
- Drafts survive tab changes and failed requests.
- Comment controls are keyboard accessible.
- Comment errors preserve user input.
