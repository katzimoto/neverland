import styles from "./Skeleton.module.css";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  rounded?: boolean;
}

export function Skeleton({ width, height, className = "", rounded = false }: SkeletonProps) {
  return (
    <span
      className={`${styles.skeleton} ${rounded ? styles.rounded : ""} ${className}`}
      style={{ width, height }}
      aria-hidden
    />
  );
}

interface SkeletonRowProps {
  lines?: number;
  className?: string;
}

export function SkeletonRow({ lines = 3, className = "" }: SkeletonRowProps) {
  return (
    <div className={`${styles.row} ${className}`} aria-label="Loading">
      <Skeleton height={16} width="60%" />
      {Array.from({ length: lines - 1 }).map((_, i) => (
        <Skeleton key={i} height={14} width={i % 2 === 0 ? "90%" : "75%"} />
      ))}
    </div>
  );
}
