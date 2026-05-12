import { useQuery } from "@tanstack/react-query";
import { getTranslationVersions, type TranslationVersion } from "@/api/documents";
import styles from "./TranslationVersionSelector.module.css";

interface TranslationVersionSelectorProps {
  docId: string;
  selectedVersionId: string | undefined;
  onSelect: (versionId: string | undefined) => void;
}

function isSelectableTranslationVersion(status: TranslationVersion["status"]): boolean {
  return status === "done" || status === "available";
}

export function TranslationVersionSelector({
  docId,
  selectedVersionId,
  onSelect,
}: TranslationVersionSelectorProps) {
  const { data: versions } = useQuery({
    queryKey: ["doc-translation-versions", docId],
    queryFn: () => getTranslationVersions(docId),
  });

  if (!versions?.length) return null;

  return (
    <label className={styles.wrapper}>
      <span className={styles.label}>Version</span>
      <select
        className={styles.select}
        value={selectedVersionId ?? ""}
        onChange={(e) => onSelect(e.target.value || undefined)}
        aria-label="Translation version"
      >
        <option value="">Latest</option>
        {versions.map((v: TranslationVersion) => {
          const isSelectable = isSelectableTranslationVersion(v.status);
          return (
            <option
              key={v.version_id}
              value={v.version_id}
              disabled={!isSelectable}
            >
              {v.label} {!isSelectable ? `(${v.status})` : ""}
            </option>
          );
        })}
      </select>
    </label>
  );
}
