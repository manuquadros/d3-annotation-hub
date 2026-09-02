## Deployment

Sample config.toml

```toml
[authentication]
access_token_expire_minutes = 15
algorithm = "EdDSA"
D3HUB_PKPATH = "~/.ssh/d3annotation" # although this can also be set as an env variable
```

### Private key for JSON Web Tokens

The [config](src/ahbackend/config/__init__.py) searches for a private key in the location defined by `D3HUB_PKPATH`. You have to set this variable either in config.toml as above or as an environment variable in your system.

## Development environment

Dependencies are managed with `pdm`; the project's commands run through `pdm run` (`dev`, `lint`, `fmt`, `test` — see `[tool.pdm.scripts]` in `pyproject.toml`).

Do not assume the virtualenv is at `backend/.venv`. Where `pdm` places it depends on the developer's `venv.in_project` setting: pdm's own default is `backend/.venv`, while `venv.in_project = false` puts it under `venv.location` (default `~/.local/share/pdm/venvs/`), where the generated directory name embeds a path hash and a Python version. Tooling that needs the interpreter directly should read the path `pdm` recorded in `.pdm-python` instead of hardcoding a venv location. That file is gitignored, so it is absent from a fresh clone and from any `git worktree` — resolve it from the primary checkout.
