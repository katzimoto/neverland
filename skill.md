# SKILLS.md

> Shared skill definitions consumed by both the **Developer** and **Reviewer**
> agents declared in `AGENTS.md`.
> Every skill lists: purpose, commands, configuration pointers, thresholds,
> and the CI step that enforces it.

-----

## 1. Test-Driven Development (TDD)

### Philosophy

Write the test first. The implementation exists to make tests pass — not the
other way around. Tests are the executable specification.

### Cycle

```
Red  → write a failing test that describes the desired behaviour
Green → write the minimal code to pass the test
Refactor → clean up without changing observable behaviour
```

### File conventions

|Language            |Test runner|Location            |Pattern    |
|--------------------|-----------|--------------------|-----------|
|TypeScript / JS     |Vitest     |`tests/unit/`       |`*.test.ts`|
|TypeScript / JS     |Playwright |`tests/e2e/`        |`*.spec.ts`|
|Python              |pytest     |`tests/unit/`       |`test_*.py`|
|Python (integration)|pytest     |`tests/integration/`|`test_*.py`|

### Coverage thresholds

```yaml
# vitest.config.ts / pytest threshold
unit:
  lines:    90
  branches: 85
  functions: 90
statements: 90

integration:
  lines:    75
  branches: 70
```

Agents **must not** merge code below these thresholds.
The Developer agent must include a coverage report in the PR body.

### Commands

```bash
# JavaScript / TypeScript
npx vitest run --coverage

# Python
pytest --cov=src --cov-branch --cov-report=term-missing \
       --cov-fail-under=90 tests/
```

### What to test

- **Happy path** — expected inputs produce expected outputs.
- **Edge cases** — empty input, boundary values, max values.
- **Error paths** — invalid input throws / returns correct error.
- **Side effects** — DB writes, HTTP calls, file I/O (use mocks/stubs).
- **Async behaviour** — timeouts, retries, race conditions.

### What not to test

- Third-party library internals.
- Implementation details (test behaviour, not code structure).
- Trivial getters/setters unless they contain logic.

-----

## 2. Linting

All linters run in `--fix` mode during development and in strict (no-fix,
exit-code 1 on violation) mode in CI.

### JavaScript / TypeScript

**Tool:** ESLint + Prettier + typescript-eslint

```bash
# Fix locally
npx eslint --fix "src/**/*.{ts,tsx}" "tests/**/*.{ts,tsx}"
npx prettier --write "src/**/*.{ts,tsx,json,md}"

# CI (strict — no auto-fix)
npx eslint "src/**/*.{ts,tsx}" "tests/**/*.{ts,tsx}"
npx prettier --check "src/**/*.{ts,tsx,json,md}"
```

Minimum required ESLint rules (`eslint.config.ts`):

```ts
rules: {
  "@typescript-eslint/no-explicit-any": "error",
  "@typescript-eslint/explicit-function-return-type": "warn",
  "no-console": ["warn", { allow: ["warn", "error"] }],
  "eqeqeq": ["error", "always"],
  "no-unused-vars": "error",
  "prefer-const": "error",
  "no-var": "error",
}
```

### Python

**Tools:** Ruff (lint + format) + mypy (type checking)

```bash
# Fix locally
ruff check --fix src/ tests/
ruff format src/ tests/

# Type check
mypy src/ --strict

# CI (strict)
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/ --strict
```

Minimum `pyproject.toml` settings:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "TCH"]

[tool.mypy]
strict = true
python_version = "3.11"
```

### Shell scripts

```bash
shellcheck scripts/**/*.sh
```

### GitHub Actions workflows

```bash
actionlint .github/workflows/*.yml
```

### Pre-commit (local enforcement)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks: [{ id: ruff, args: [--fix] }, { id: ruff-format }]
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.3.0
    hooks: [{ id: eslint, additional_dependencies: [eslint, typescript-eslint] }]
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v4.0.0-alpha.8
    hooks: [{ id: prettier }]
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks: [{ id: shellcheck }]
```

-----

## 3. Documentation

### Docstring standards

#### Python (Google style)

```python
def calculate_discount(price: float, rate: float) -> float:
    """Calculate the discounted price.

    Args:
        price: Original price in the base currency.
        rate: Discount rate as a decimal (e.g. 0.15 for 15 %).

    Returns:
        Discounted price rounded to 2 decimal places.

    Raises:
        ValueError: If rate is not in the range [0, 1].

    Example:
        >>> calculate_discount(100.0, 0.15)
        85.0
    """
```

#### TypeScript (TSDoc)

```ts
/**
 * Calculate the discounted price.
 *
 * @param price - Original price in the base currency.
 * @param rate - Discount rate as a decimal (e.g. `0.15` for 15 %).
 * @returns Discounted price rounded to 2 decimal places.
 * @throws {RangeError} When `rate` is outside `[0, 1]`.
 *
 * @example
 * ```ts
 * calculateDiscount(100, 0.15); // 85
 * ```
 */
```

### Required docs per PR

|Item                         |Required when                      |
|-----------------------------|-----------------------------------|
|Inline docstring             |Every new or modified public symbol|
|`docs/specs/<feature>.md`    |New feature                        |
|`docs/adr/<number>-<slug>.md`|Architecture decision              |
|`CHANGELOG.md` entry         |Every merged PR                    |
|`README.md` update           |New setup step / env var / command |

### Changelog format (Keep a Changelog)

```markdown
## [Unreleased]

### Added
- Short description of new feature (#issue)

### Changed
- ...

### Fixed
- ...

### Removed
- ...
```

### Docs lint

```bash
# Check broken links
npx markdownlint-cli2 "**/*.md" --ignore node_modules
```

-----

## 4. Best Practices

### General

- **Single responsibility** — one function does one thing.
- **Fail fast** — validate inputs at the boundary; never let bad data travel deep.
- **Immutability by default** — prefer `const`, frozen objects, and pure functions.
- **Explicit over implicit** — name things clearly; avoid magic numbers/strings
  (use named constants).
- **No silent failures** — every error must be either handled or explicitly
  propagated; never swallow exceptions.

### Security

```bash
# JS dependency audit
npm audit --audit-level=high

# Python dependency audit
pip-audit

# Secret scanning (run in CI on every push)
trufflehog filesystem . --only-verified
```

Hard rules:

- No hardcoded credentials, tokens, or keys — use environment variables.
- Sanitise all external input before use.
- Use parameterised queries; never string-interpolate SQL.
- Set least-privilege permissions on any file, process, or IAM role.

### Performance

- Prefer `async/await` over callbacks; never block the event loop.
- Cache expensive computations (memoise or use a cache layer).
- Paginate or stream large data sets; never load unbounded result sets.
- Profile before optimising — fix measured bottlenecks, not assumed ones.

### Error handling

```python
# Python — always use typed, descriptive exceptions
class PaymentDeclinedError(ValueError):
    """Raised when the payment gateway declines a charge."""
```

```ts
// TypeScript — use Result types or typed error unions, not generic Error
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
```

### Dependency management

- Pin all dependencies to exact versions in lock files (`package-lock.json`,
  `poetry.lock`, `uv.lock`).
- Group runtime vs dev dependencies correctly.
- Remove unused dependencies — checked via `depcheck` (JS) / `deptry` (Python).

```bash
npx depcheck
uvx deptry src
```

-----

## 5. CI Skill Pipeline

The skills above map to the following GitHub Actions jobs.
All jobs run on `ubuntu-latest` with dependency caching.

```yaml
jobs:

  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npx eslint "src/**/*.{ts,tsx}"
      - run: npx prettier --check "src/**/*.{ts,tsx,json,md}"
      # Python (add if applicable)
      - uses: astral-sh/setup-uv@v4
      - run: uv run ruff check src/ tests/
      - run: uv run ruff format --check src/ tests/
      - run: uv run mypy src/ --strict

  test:
    name: Test & Coverage
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm }
      - run: npm ci
      - run: npx vitest run --coverage
      - uses: codecov/codecov-action@v4
        with: { fail_ci_if_error: true }
      # Python
      - run: uv run pytest --cov=src --cov-branch --cov-fail-under=90 tests/

  security:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
      - run: uv run pip-audit
      - uses: trufflesecurity/trufflehog@v3
        with: { path: . }

  docs-lint:
    name: Docs Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx markdownlint-cli2 "**/*.md" --ignore node_modules

  codex-review:
    name: Codex Reviewer
    runs-on: ubuntu-latest
    needs: [lint, test, security]
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - run: |
          codex run \
            --agent reviewer \
            --skills SKILLS.md \
            --pr "${{ github.event.pull_request.number }}"
      - uses: actions/upload-artifact@v4
        with:
          name: review-${{ github.event.pull_request.number }}
          path: review/${{ github.event.pull_request.number }}.md
      - run: |
          gh pr review "${{ github.event.pull_request.number }}" \
            --body-file "review/${{ github.event.pull_request.number }}.md"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Job dependency graph

```
lint ──┐
       ├──▶ test ──┐
       │            ├──▶ codex-review
security ──┘        │
                    │
docs-lint ──────────┘
```

-----

## 6. Token Budget Guidelines

Both agents must respect these budgets to keep CI costs predictable.

|Operation                       |Max tokens|
|--------------------------------|----------|
|Context summarisation (per file)|300       |
|Single agent turn               |4 096     |
|Review output                   |2 048     |
|Total per PR (Developer)        |16 000    |
|Total per PR (Reviewer)         |8 000     |

**Strategies to stay within budget:**

- Load only the diff, never the full repository.
- Summarise long files to their public API surface before including them.
- Chunk large features into multiple smaller PRs.
- Cache repeated tool results within a session (e.g., `npm ls` output).
- Prefer structured output (JSON / YAML) over verbose prose in inter-agent
  communication.