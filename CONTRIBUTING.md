# Contributing to Energy Window Tracker

Thank you for your interest in contributing. This document covers testing and development setup.

## Testing

The test suite follows the [Home Assistant development testing](https://developers.home-assistant.io/docs/development_testing/) framework:

- **pytest** for unit tests; integration is set up via `hass.config_entries.async_setup`; assertions use `hass.states` and the entity registry.
- **Ruff** for linting (required; run locally before committing and in CI).

### Running tests locally

From the repo root, run tests and lint; both must pass before submitting.

```bash
pip install -r requirements_test.txt
pytest tests/ -v
ruff check custom_components/ tests/
```

### Pre-commit hook (recommended)

You can run tests and the linter automatically before each commit using [pre-commit](https://pre-commit.com/).

1. Install dependencies and the hook:

   ```bash
   pip install -r requirements_test.txt
   pre-commit install
   ```

2. On every `git commit`, pre-commit will run **ruff** then **pytest**. The commit is blocked if either fails.

3. Run the same checks manually (e.g. before pushing) without committing:

   ```bash
   pre-commit run --all-files
   ```

To skip the hook once (use sparingly): `git commit --no-verify`.

Useful options (as in the [HA testing docs](https://developers.home-assistant.io/docs/development_testing/#running-a-limited-test-suite)):

```bash
# Stop after the first failure
pytest tests/ -v -x

# Run a single test by name
pytest tests/ -v -k test_user_flow_show_form

# With coverage (optional)
pytest tests/ -v --cov=custom_components.energy_window_tracker --cov-report=term-missing
```

### Linting

Run Ruff before committing or opening a PR. CI will fail if lint does not pass.

```bash
pip install ruff
ruff check custom_components/ tests/
```

### GitHub Actions pipeline

A **Test** workflow runs on every push and pull request to `main`/`master`:

1. **pytest** – Runs the full test suite on Python 3.11 and 3.12.
2. **Ruff** – Lints `custom_components/` and `tests/`.

**Setup:** No extra configuration is needed. Ensure the repo has Actions enabled (Settings → Actions → General → “Allow all actions”).

**To add the pipeline** if it’s not there: the workflow file is `.github/workflows/test.yml`. Commit and push it; the first run will appear under the **Actions** tab. Fix any failing tests or lint issues so the workflow stays green.
