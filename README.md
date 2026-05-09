# neverland

Neverland is a local-first knowledge intelligence system for private document
corpora. The canonical product spec is `spec-v4.pdf`.

## How To Run

Neverland includes a production-style Docker Compose runtime. It starts the API,
frontend container, migration job, and required infrastructure as separate
services.

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` before using real data. At minimum, change:

   - `POSTGRES_PASSWORD`
   - `POSTGRES_URL` so it uses the same password
   - `JWT_SECRET`

3. Start the local product:

   ```bash
   docker compose up --build
   ```

4. Open the runtime:

   - Frontend: `http://localhost:8080`
   - API health: `http://localhost:8000/health`
   - Frontend health: `http://localhost:8080/health`

Useful commands:

```bash
docker compose config
docker compose run --rm migrate
docker compose logs -f api frontend migrate
docker compose down
docker compose down -v
```

See `docs/operations/production-compose.md` for the full operations guide,
including service layout, annotated environment variables, reset behavior,
backup and restore guidance, health checks, troubleshooting, and current
limitations.
