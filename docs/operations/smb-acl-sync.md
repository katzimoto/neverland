# SMB NTFS ACL Sync

Neverland can optionally synchronize a conservative NTFS ACL snapshot for SMB
sources and use that snapshot as an additional document visibility gate.

This feature is **disabled by default** and is intended for deployments that have
validated their SMB service account, Windows principal mappings, and rollback
procedure. ACL-derived permissions can only further restrict access after the
existing Neverland source-level grant succeeds; they never grant access on their
own.

## Prerequisites

- The source type is `smb`.
- The global feature flag `feature.smb_acl_sync` is set to `true` through system
  configuration or the `FEATURE_SMB_ACL_SYNC=true` environment override.
- The SMB source config contains `"acl_sync_enabled": true`.
- The SMB service account can read file contents and file security descriptors
  (`READ_CONTROL`) for every indexed file.
- Neverland groups already exist for the users who should receive access.
- Operators create explicit principal mappings from Windows principals to
  Neverland groups.

Both the global flag and per-source flag must be enabled before ACL extraction or
enforcement applies. If either flag is disabled, the source uses the existing
Neverland source-grant model only.

## Enabling ACL sync

1. Enable the global feature flag:

   ```bash
   FEATURE_SMB_ACL_SYNC=true
   ```

   Or update `system_config` so `feature.smb_acl_sync` is `true`.

2. Opt in each SMB source by adding the source config key:

   ```json
   {
     "server": "fileserver.local",
     "share": "department",
     "base_path": "/legal/contracts",
     "username": "svc-neverland",
     "password": "...",
     "domain": "CORP",
     "acl_sync_enabled": true
   }
   ```

3. Map Windows principals to Neverland groups with the admin API:

   ```bash
   curl -X POST \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:8000/admin/sources/$SOURCE_ID/acl-mappings \
     -d '{"windows_principal":"S-1-5-21-...-1001","group_id":"'$GROUP_ID'"}'
   ```

   `windows_principal` is normalized to uppercase and may be a SID or a domain
   qualified name such as `CORP\LEGAL_TEAM`. SID mappings are preferred because
   SIDs are stable and globally unique.

4. Run a normal source sync. ACL snapshots are stored in `document_acls`; explicit
   mappings are stored in `smb_principal_mappings`.

## Enforcement behavior

When ACL sync is effectively enabled for an SMB source, a document is visible only
when both conditions are true:

1. The user has the existing Neverland source-level grant.
2. The user belongs to a Neverland group mapped to a matching Windows allow ACE
   for the document, and no mapped deny ACE matches.

Deny entries override allow entries. Unknown or unmapped principals do not grant
access. A document with no matching mapped allow ACE is hidden.

The ACL gate is applied to search results, preview, download, translation and
intelligence endpoints, related documents, RAG citations/context, expertise
evidence, comments, and annotations where those paths depend on document access.

## Fail-closed cases

Neverland hides an ACL-enabled SMB document when any of these conditions occur:

- ACL read fails during sync.
- ACL data is missing, malformed, unsupported, or ambiguous.
- No `document_acls` row exists for the document.
- A stored ACL row has a non-null sanitized error.
- The only relevant ACL principals are unknown or unmapped.
- A mapped deny ACE matches one of the user's groups.

ACL read failures do not delete documents or route them to the DLQ. Documents stay
indexed but are filtered at access time until ACL data and mappings are fixed or
ACL sync is disabled.

## Security and privacy notes

- Source-level grants remain mandatory and are evaluated before ACL grants.
- Raw ACL blobs are not exposed through user document metadata.
- Logs must not include credentials, raw ACLs, SIDs, file contents, document text,
  or sensitive remote paths.
- Admin mapping APIs expose principal strings only to administrators.

## Limitations

- Nested AD group expansion is not implemented.
- LDAP `objectSid` auto-resolution is not implemented.
- Windows access masks are stored but not interpreted beyond allow/deny ACE type.
- Deny-wins behavior is conservative and does not model full Windows inheritance
  ordering semantics.
- Live SMB/AD integration tests are out of scope for CI.
- Search and RAG use post-filtering for ACLs in this MVP, so result counts may be
  lower after filtering than the backend search hit count.

## Rollback and disable path

To disable ACL enforcement immediately, set `feature.smb_acl_sync=false` or remove
`FEATURE_SMB_ACL_SYNC=true`, then restart/reload the API configuration as needed.
Per-source `acl_sync_enabled` can also be set to `false` for a narrower rollback.
Existing ACL rows and mappings remain in the database but are ignored while either
flag is disabled.

## Troubleshooting

- Verify `feature.smb_acl_sync=true` and source `acl_sync_enabled=true`.
- Verify the source type is `smb`; non-SMB sources ignore ACL rows.
- Verify the SMB service account has `READ_CONTROL` on the files.
- Verify a `document_acls` row exists and its `error` is null.
- Verify the Windows principal is mapped to the correct Neverland group.
- Prefer SID mappings over `DOMAIN\group` mappings when possible.
