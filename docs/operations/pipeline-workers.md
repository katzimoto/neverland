# Pipeline Worker Operations Guide

This guide is for operators running and monitoring the Tomorrowland pipeline
worker processes. It covers worker architecture, metrics, troubleshooting, and
restart procedures.

---

## Worker Architecture

Tomorrowland's document ingestion pipeline runs as two independent
long-running worker processes that share a PostgreSQL-backed job queue.

### pipeline-worker

- **Process**: `python -m services.pipeline.runner`
- **Compose service**: `pipeline-worker`
- **Job type claimed**: `process_document`
- **Worker type label**: `pipeline`

The pipeline-worker extracts text, runs translation, chunks content, and
indexes documents into Elasticsearch. After a successful `process_document`
job, it automatically enqueues a `vector_index_document` job for downstream
vector indexing.

### vector-worker

- **Process**: `python -m services.pipeline.vector_worker`
- **Compose service**: `vector-worker`
- **Job type claimed**: `vector_index_document`
- **Worker type label**: `vector`

The vector-worker encodes document chunks via Ollama and upserts Qdrant points.
It runs independently of the pipeline-worker and pulls only
`vector_index_document` jobs from the queue.

### Shared queue

Both workers consume from the same `pipeline_jobs` table in PostgreSQL via
`SELECT … FOR UPDATE SKIP LOCKED`. This is **DB polling**, not a Kafka
consumer. There is no Kafka consumer lag concept here; queue depth is the
relevant backlog signal. Multiple replicas of either worker can run safely —
the `SKIP LOCKED` claim prevents duplicate processing.

### Job flow

```
sync-now API call
  → enqueue process_document
      → pipeline-worker claims job
          → extract / translate / chunk / Elasticsearch index
          → on success: enqueue vector_index_document
              → vector-worker claims job
                  → encode chunks / upsert Qdrant
```

---

## Job States

| State | Meaning |
|-------|---------|
| `pending` | Waiting to be claimed by a worker |
| `running` | Actively held by a worker under a lock |
| `retry` | Failed attempt; will become claimable after back-off delay |
| `succeeded` | Completed successfully |
| `dead_letter` | Exhausted all attempts; requires operator attention |

Queue depth is sampled across all states on every loop iteration. Only
`pending` and `retry` rows are claimable; `running` rows are locked.

---

## Metrics Reference

All pipeline worker metrics are registered in `src/shared/metrics.py` and
exposed on the same Prometheus endpoint as the rest of the application.

### `tomorrowland_worker_heartbeat_timestamp_seconds`

**Type**: Gauge  
**Labels**: `worker_type`, `worker_id`

Unix timestamp set to the current time at the start of every worker loop
iteration. Use this to detect stale or stopped workers.

```promql
# Seconds since last heartbeat per worker
time() - tomorrowland_worker_heartbeat_timestamp_seconds
```

A value above ~30 seconds (several poll intervals) means the worker loop has
stalled or the process has stopped. Alert when this exceeds 60–120 seconds
depending on acceptable lag.

---

### `tomorrowland_pipeline_queue_depth`

**Type**: Gauge  
**Labels**: `status`, `job_type`

Current number of jobs in the queue broken down by status and job type.
Sampled via a `COUNT … GROUP BY status, job_type` query on each loop
iteration. Values are a point-in-time snapshot, not a running total.

```promql
# Pending backlog for process_document jobs
tomorrowland_pipeline_queue_depth{status="pending", job_type="process_document"}

# All dead-letter jobs across types
sum by (job_type) (
  tomorrowland_pipeline_queue_depth{status="dead_letter"}
)
```

A rising `pending` depth that does not drain means the worker is not keeping
up or has stopped. A rising `dead_letter` depth requires operator investigation.

---

### `tomorrowland_pipeline_jobs_claimed_total`

**Type**: Counter  
**Labels**: `worker_type`, `job_type`

Total jobs successfully claimed from the queue. Incremented immediately after
`claim_next` returns a job, before processing begins.

```promql
# Claim throughput over 5 minutes
rate(tomorrowland_pipeline_jobs_claimed_total[5m])
```

Compare claim rate to succeeded rate. A persistent gap between claimed and
succeeded indicates failures are accumulating.

---

### `tomorrowland_pipeline_jobs_succeeded_total`

**Type**: Counter  
**Labels**: `worker_type`, `job_type`

Total jobs completed successfully.

```promql
rate(tomorrowland_pipeline_jobs_succeeded_total[5m])
```

---

### `tomorrowland_pipeline_jobs_retried_total`

**Type**: Counter  
**Labels**: `worker_type`, `job_type`

Total jobs scheduled for retry after a failed attempt that has not yet
exhausted `max_attempts`. A retry moves the job back to a claimable state
after a back-off delay.

```promql
# Retry rate over 5 minutes
rate(tomorrowland_pipeline_jobs_retried_total[5m])
```

A sustained non-zero retry rate indicates a recurring transient error.
A rate that closely tracks the claim rate indicates near-total failure.

---

### `tomorrowland_pipeline_jobs_dead_lettered_total`

**Type**: Counter  
**Labels**: `worker_type`, `job_type`

Total jobs moved to `dead_letter` state after exhausting all retry attempts.
Dead-letter jobs do not run again without explicit operator intervention.

```promql
# Dead-letter rate over 1 hour
rate(tomorrowland_pipeline_jobs_dead_lettered_total[1h])
```

Any increase in this counter requires investigation. Dead-letter growth means
documents are failing permanently and will not be indexed without manual
re-queueing.

---

### `tomorrowland_pipeline_jobs_stale_lock_reaped_total`

**Type**: Counter  
**Labels**: `worker_type`

Total jobs reset from `running` back to `pending` because their lock expired.
Stale locks occur when a worker process crashes or is killed while holding a
running job. The reap runs every 60 seconds inside the worker loop.

```promql
rate(tomorrowland_pipeline_jobs_stale_lock_reaped_total[10m])
```

Occasional reaping is normal after restarts. Repeated reaping at a high rate
suggests workers are crashing mid-job — check loop error counts and logs.

---

### `tomorrowland_pipeline_job_duration_seconds`

**Type**: Histogram  
**Labels**: `worker_type`, `job_type`, `stage`, `outcome`  
**Buckets**: 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0 (seconds)

Processing duration from claim to outcome for each job attempt. Recorded for
every outcome, including retries and dead-letters.

| Worker | Stage value |
|--------|-------------|
| pipeline-worker | `process` |
| vector-worker | `vector_encode` |

Outcome values: `succeeded`, `retried`, `dead_lettered`

```promql
# p95 duration for succeeded process_document jobs
histogram_quantile(0.95,
  rate(tomorrowland_pipeline_job_duration_seconds_bucket{
    job_type="process_document",
    outcome="succeeded"
  }[10m])
)

# p99 duration for vector encoding
histogram_quantile(0.99,
  rate(tomorrowland_pipeline_job_duration_seconds_bucket{
    job_type="vector_index_document",
    outcome="succeeded"
  }[10m])
)
```

---

### `tomorrowland_worker_loop_errors_total`

**Type**: Counter  
**Labels**: `worker_type`, `error_type`

Unhandled exceptions that escaped the inner job-processing call and were
caught by the outer loop error handler. This is distinct from job-level
failures (which increment retry or dead-letter counters): a loop error means
the worker loop itself encountered an unexpected exception and paused before
continuing.

```promql
rate(tomorrowland_worker_loop_errors_total[5m])
```

Any non-zero rate here warrants immediate log inspection. The `error_type`
label contains the Python exception class name.

---

## Queue Depth Sampling

Queue depth is sampled using a `COUNT … GROUP BY status, job_type` query
executed inside each worker loop iteration (before claiming the next job).
The gauge values are point-in-time snapshots updated at the worker's poll
rate (default 1 second). Because snapshots are taken by the worker process,
if all workers stop, queue depth gauges will not update. A stale heartbeat
combined with stale queue depth is a strong signal that all workers of that
type have stopped.

---

## Heartbeat Monitoring

Each worker updates its heartbeat at the top of every loop iteration,
regardless of whether a job was available. The gauge holds a Unix timestamp
(seconds since epoch).

To detect a stale or stopped worker:

```promql
# Seconds since last heartbeat — alert when > 60 or 120 seconds
time() - tomorrowland_worker_heartbeat_timestamp_seconds{worker_type="pipeline"}
time() - tomorrowland_worker_heartbeat_timestamp_seconds{worker_type="vector"}
```

The `worker_id` label identifies the specific process instance (set at
startup). Multiple replicas of the same worker type will each appear as a
separate time series.

---

## Retry and Dead-Letter Behavior

### Retry

When a job fails and `attempts < max_attempts`, the worker calls `mark_retry`.
The job is returned to a claimable state after an exponential back-off delay
(managed by the job repository). The `tomorrowland_pipeline_jobs_retried_total`
counter increments and a duration observation with `outcome="retried"` is
recorded.

### Dead-letter

When a job fails and `attempts >= max_attempts`, the worker calls
`mark_dead_letter`. The job enters `dead_letter` state and will not be
claimed again automatically. The
`tomorrowland_pipeline_jobs_dead_lettered_total` counter increments.

### Operational meaning of dead-letter growth

Growing dead-letter depth means documents are failing permanently. Common
causes include:

- A dependency (Elasticsearch, Qdrant, Ollama) is consistently unavailable
- A document has malformed content that triggers a reproducible exception
- A code bug affects all documents of a particular type

Dead-letter jobs require operator investigation. Once the root cause is
resolved, jobs can be re-queued via the admin API.

---

## Stale Lock Reaping

### Why it exists

When a worker process is killed mid-job (SIGKILL, OOM, container restart
without graceful shutdown), the job remains in `running` state with no
worker holding it. Without reaping, those jobs would be stuck forever.

### When it runs

The reap check runs inside the worker loop every 60 seconds
(`_REAP_INTERVAL_SECONDS`). It calls `job_repo.reap_stale_locks()`, which
finds `running` jobs whose lock timestamp has expired and resets them to
`pending` so they can be reclaimed.

### What it means if stale locks are repeatedly reaped

Occasional reaping after a restart is expected and harmless. Sustained reaping
at a non-trivial rate means workers are regularly dying mid-job. Check:

1. `tomorrowland_worker_loop_errors_total` — unhandled loop exceptions
2. Container OOM events (`docker inspect <container>` or system logs)
3. Dependency health (Elasticsearch, Qdrant, Postgres) — connection resets
   can cause worker crashes

---

## Safe Labels and Cardinality

All metric labels must remain **bounded and low-cardinality**. The following
values must **never** appear as label values or label names:

- Document IDs or UUIDs
- Raw file paths
- User data or usernames
- Document text content
- Credentials or secrets
- Exception messages (use exception class name only — `error_type` labels
  contain only the Python class name such as `ValueError`, not the message)

The `safe_label_value` helper in `src/shared/metrics.py` enforces a 100-character
cap and normalizes empty values to `"unknown"`. This is a minimum safeguard.
Operators adding new instrumentation must review label values before deploying
to ensure cardinality is bounded.

High-cardinality labels cause Prometheus memory growth and can make scraping
unreliable. If a new label candidate has unbounded values (one per document,
per user, per path), it belongs in structured logs, not in a metric label.

---

## Troubleshooting Playbook

### Worker stopped

**Signals**: Heartbeat age exceeds threshold; queue depth gauge not updating;
no new `succeeded` or `claimed` increments.

1. Check container state:
   ```
   docker compose ps pipeline-worker
   docker compose ps vector-worker
   ```
2. Read recent logs:
   ```
   docker compose logs --tail=100 pipeline-worker
   docker compose logs --tail=100 vector-worker
   ```
3. Restart the stopped worker (see [Restart Guidance](#restart-guidance)).

---

### Queue backlog growing

**Signals**: `tomorrowland_pipeline_queue_depth{status="pending"}` rising;
claim rate low relative to enqueue rate.

1. Confirm workers are running and heartbeat is fresh.
2. Check worker logs for errors.
3. Check `tomorrowland_worker_loop_errors_total` for loop-level failures.
4. Verify dependencies are healthy (Postgres, Elasticsearch, Qdrant, Ollama).
5. If workers are processing but slowly, check p95/p99 job duration and
   look for resource contention.

---

### Retry count increasing

**Signals**: `tomorrowland_pipeline_jobs_retried_total` rate rising.

1. Check `tomorrowland_pipeline_job_duration_seconds{outcome="retried"}` for
   which job types and stages are failing.
2. Check worker logs for the exception class name associated with retries.
3. Check dependency health — connection errors and timeouts are the most
   common transient failure sources.
4. If the retry rate tracks the claim rate, assume near-total failure of that
   worker type. Investigate logs and dependency health immediately.

---

### Dead-letter count increasing

**Signals**: `tomorrowland_pipeline_jobs_dead_lettered_total` rate rising;
`tomorrowland_pipeline_queue_depth{status="dead_letter"}` growing.

1. Identify which `job_type` is dead-lettering using the counter labels.
2. Read worker logs for the failure pattern (exception class name).
3. Diagnose and fix the underlying cause (dependency failure, malformed data,
   code bug).
4. Re-queue dead-letter jobs via the admin API once the cause is resolved.

---

### Stale locks repeatedly reaped

**Signals**: `tomorrowland_pipeline_jobs_stale_lock_reaped_total` rate
non-trivial and sustained.

1. Check for container OOM kills or SIGKILL restarts in system and Docker
   logs.
2. Check `tomorrowland_worker_loop_errors_total` for crash patterns.
3. Check dependency connection stability — unexpected disconnects can cause
   mid-job panics.
4. A single reap after a planned restart is normal. Repeated reaping indicates
   workers are crashing mid-job.

---

### Loop errors increasing

**Signals**: `tomorrowland_worker_loop_errors_total` rate non-zero.

1. Check logs for the `error_type` class name and full stack trace.
2. Loop errors pause the worker for one poll interval before resuming — the
   worker does not stop, but throughput is reduced.
3. A sustained loop error rate can lead to queue backlog and should be treated
   as urgent.

---

### Job duration p95/p99 high

**Signals**: `histogram_quantile` on
`tomorrowland_pipeline_job_duration_seconds` shows high tail latency.

1. For `pipeline-worker` / stage `process`: investigate Elasticsearch
   indexing latency, LibreTranslate response time, extractor performance.
2. For `vector-worker` / stage `vector_encode`: investigate Ollama encoding
   latency and Qdrant upsert time.
3. Check system resource usage (CPU, memory, I/O) on the worker host.
4. High p99 with normal p50 may indicate specific documents (large files,
   unusual content) are outliers — check document size distribution.

---

## Restart Guidance

Both workers are stateless processes that read from the shared DB queue. A
restart is safe at any time:

- Jobs in `running` state that were held by the stopping worker will have
  their lock reaped on the next reap cycle (within 60 seconds) and returned
  to `pending`.
- No in-flight state is lost; job progress is tracked in the database.

### Using Docker Compose

```bash
# Restart a single worker without affecting other services
docker compose restart pipeline-worker
docker compose restart vector-worker

# Stop and start (for a clean container)
docker compose stop pipeline-worker && docker compose start pipeline-worker
docker compose stop vector-worker && docker compose start vector-worker
```

### Checking status after restart

```bash
docker compose ps pipeline-worker
docker compose ps vector-worker
docker compose logs --tail=50 pipeline-worker
docker compose logs --tail=50 vector-worker
```

After restart, confirm the heartbeat gauge updates within a few seconds and
that the loop error counter is not incrementing.

---

## See Also

- `src/services/pipeline/runner.py` — pipeline-worker loop implementation
- `src/services/pipeline/vector_worker.py` — vector-worker loop implementation
- `src/shared/metrics.py` — metric registration and label safety helpers
- `docs/operations/production-compose.md` — Compose service layout and general operations
- `docs/operations/air-gapped-deployment.md` — offline deployment guide
