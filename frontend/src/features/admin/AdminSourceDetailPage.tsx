import { useState } from "react";
import { useParams, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, X } from "lucide-react";
import { adminApi } from "@/api/admin";
import { Button } from "@/components/primitives/Button";
import { Badge } from "@/components/primitives/Badge";
import { SkeletonRow } from "@/components/primitives/Skeleton";
import { EmptyState } from "@/components/primitives/EmptyState";
import { useToast } from "@/components/primitives/ToastContext";
import styles from "./AdminSourcesPage.module.css";

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminSourceDetailPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { show: showToast } = useToast();
  const { sourceId } = useParams({ from: "/app/admin/sources/$sourceId" });
  const [addingGroup, setAddingGroup] = useState(false);

  const { data: source, isLoading, isError } = useQuery({
    queryKey: ["admin-source", sourceId],
    queryFn: () => adminApi.getSource(sourceId!),
    enabled: !!sourceId,
  });

  const { data: allGroups } = useQuery({
    queryKey: ["admin-groups"],
    queryFn: () => adminApi.listGroups(),
  });

  const grantMutation = useMutation({
    mutationFn: (groupId: string) => adminApi.grantPermission(sourceId!, groupId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-source", sourceId] });
      setAddingGroup(false);
      showToast("success", "Group granted access.");
    },
    onError: () => {
      showToast("error", "Failed to grant access.");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (groupId: string) => adminApi.revokePermission(sourceId!, groupId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-source", sourceId] });
      showToast("success", "Group access revoked.");
    },
    onError: () => {
      showToast("error", "Failed to revoke access.");
    },
  });

  if (isLoading) {
    return (
      <div className={styles.page}>
        <SkeletonRow count={8} />
      </div>
    );
  }

  if (isError || !source) {
    return (
      <div className={styles.page}>
        <EmptyState title="Source not found" body="The source could not be loaded." />
      </div>
    );
  }

  const availableGroups = (allGroups || []).filter(
    (g) => !source.groups.some((sg) => sg.id === g.id),
  );

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Button variant="secondary" size="sm" onClick={() => navigate({ to: "/admin" })}>
          <ArrowLeft size={16} />
          Back
        </Button>
        <h1 className={styles.title}>{source.name}</h1>
        <Badge variant={source.enabled ? "success" : "neutral"}>
          {source.enabled ? "Enabled" : "Disabled"}
        </Badge>
      </div>

      <div className={styles.section}>
        <h2>Configuration</h2>
        <dl className={styles.dl}>
          <dt>Type</dt>
          <dd>{source.type}</dd>
          <dt>Path</dt>
          <dd>{source.path || "—"}</dd>
          <dt>Language</dt>
          <dd>{source.source_language || "—"}</dd>
          {Object.entries(source.config).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd><code>{String(value)}</code></dd>
            </div>
          ))}
        </dl>
      </div>

      <div className={styles.section}>
        <h2>Sync Status</h2>
        {source.last_sync_status ? (
          <dl className={styles.dl}>
            <dt>Status</dt>
            <dd>
              <Badge variant={source.last_sync_status === "failed" ? "danger" : "success"}>
                {source.last_sync_status}
              </Badge>
            </dd>
            <dt>Indexed</dt>
            <dd>{source.last_sync_indexed ?? 0}</dd>
            <dt>Skipped</dt>
            <dd>{source.last_sync_skipped ?? 0}</dd>
            <dt>Failed</dt>
            <dd>{source.last_sync_failed ?? 0}</dd>
            {source.last_sync_at && <dt>Last run</dt>}
            {source.last_sync_at && <dd>{formatDateTime(source.last_sync_at)}</dd>}
            {source.last_sync_error && <dt>Error</dt>}
            {source.last_sync_error && <dd className={styles.error}>{source.last_sync_error}</dd>}
          </dl>
        ) : (
          <p className={styles.mutedMeta}>Never synced</p>
        )}
      </div>

      <div className={styles.section}>
        <h2>Validation</h2>
        {source.last_validation_status ? (
          <dl className={styles.dl}>
            <dt>Status</dt>
            <dd>
              <Badge variant={source.last_validation_status === "ok" ? "success" : "danger"}>
                {source.last_validation_status}
              </Badge>
            </dd>
            {source.last_validated_at && <dt>Last checked</dt>}
            {source.last_validated_at && <dd>{formatDateTime(source.last_validated_at)}</dd>}
            {source.last_validation_error && <dt>Error</dt>}
            {source.last_validation_error && (
              <dd className={styles.error}>{source.last_validation_error}</dd>
            )}
          </dl>
        ) : (
          <p className={styles.mutedMeta}>Not yet validated</p>
        )}
      </div>

      <div className={styles.section}>
        <h2>Permissions</h2>
        <p className={styles.mutedMeta}>
          Groups listed here can search and open documents from this source.
        </p>

        {source.groups.length > 0 ? (
          <>
            <ul className={styles.groupList}>
              {source.groups.map((g) => (
                <li key={g.id} className={styles.groupItem}>
                  <Badge variant="neutral">{g.name}</Badge>
                  <button
                    className={styles.removeBtn}
                    type="button"
                    aria-label={`Remove ${g.name}`}
                    onClick={() => revokeMutation.mutate(g.id)}
                    disabled={revokeMutation.isPending}
                  >
                    <X size={12} />
                  </button>
                </li>
              ))}
            </ul>
            {source.groups.length === 1 && (
              <p className={styles.warning}>
                Removing this group will leave the source with no user access.
                Existing indexed documents remain, but regular users will not
                be able to search this source.
              </p>
            )}
          </>
        ) : (
          <p className={styles.mutedMeta}>
            No groups have access yet. Documents can sync, but regular users
            cannot search this source.
          </p>
        )}

        {addingGroup ? (
          <div className={styles.addGroupRow}>
            <select
              className={styles.select}
              aria-label="Select group"
              onChange={(e) => {
                if (e.target.value) {
                  grantMutation.mutate(e.target.value);
                }
              }}
              value=""
            >
              <option value="" disabled>
                Select a group…
              </option>
              {availableGroups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
            <Button variant="secondary" size="sm" onClick={() => setAddingGroup(false)}>
              Cancel
            </Button>
          </div>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setAddingGroup(true)}
            disabled={availableGroups.length === 0}
          >
            <Plus size={14} />
            Add group access
          </Button>
        )}
      </div>
    </div>
  );
}
