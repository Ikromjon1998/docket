Tutor mode: explain, write tests, review. Do not write feature code unless I say "write it".
Python 3.12, uv, FastAPI, pytest, ruff, pyright. Commits carry no AI co-author trailers.

## Commands

Everything runs through `uv run` inside the project venv (`uv sync` installs runtime + dev deps).

```bash
uv sync                                    # install runtime + dev deps
uv run pytest -q                           # run all tests
uv run pytest tests/test_health.py::test_health_returns_ok   # run one test
uv run ruff check .                        # lint
uv run ruff format --check .               # format check (`uv run ruff format .` to fix)
uv run pyright                             # type check
uv run uvicorn docket.main:app --reload    # run the API locally
```

CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check` and `pytest -q`.
Pyright runs locally only.

## Conventions

- Flat layout: code lives in `docket/` at the repo root (no `src/`). The project is not installed
  as a package, so run commands from the repo root.
- Route handlers and tests carry explicit type annotations; pyright must stay at 0 errors.
- Tests use `fastapi.testclient.TestClient` against the imported `app`, in `tests/test_*.py`.
- Git identity is the personal one (`ikromjon98.98@icloud.com`, GitHub `Ikromjon1998`), chosen
  automatically by the `includeIf` rule in `~/.gitconfig` for `~/dev/personal/`. Never set
  `user.email` manually. See `~/dev/README.md`.
