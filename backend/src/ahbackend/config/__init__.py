"""Load configuration files and set global variables."""

import os
import pathlib

import tomlkit
from cryptography.hazmat.primitives import serialization

CONFIG_DIR = pathlib.Path(__file__).parent

with pathlib.Path("config.toml").open(mode="r") as cfg:
    config = tomlkit.load(cfg)
    ALGORITHM = config.value["authentication"]["algorithm"]
    ACCESS_TOKEN_EXPIRE_MINUTES = config.value["authentication"][
        "access_token_expire_minutes"
    ]
    PK_PATH: str | None = config.value["authentication"].get(
        "D3HUB_PKPATH"
    ) or os.getenv("D3HUB_PKPATH")

if PK_PATH is None:
    raise RuntimeError(
        "Please set D3HUB_PKPATH as an environment variable or as a field in "
        "the authentication table in config.toml"
    )
with pathlib.Path(PK_PATH).expanduser().open(mode="rb") as sec:
    private_key_bytes = sec.read()
    PRIVATE_KEY = serialization.load_ssh_private_key(
        private_key_bytes, password=None
    )

with (CONFIG_DIR / "d3annotation.pub").open(mode="rb") as pubkey_file:
    public_key_bytes = pubkey_file.read()
    PUBLIC_KEY = serialization.load_ssh_public_key(public_key_bytes)
