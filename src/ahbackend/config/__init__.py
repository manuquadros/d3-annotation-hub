"""Load configuration files and set global variables."""

import os
import pathlib

import tomlkit
from cryptography.hazmat.primitives import serialization

CONFIG_DIR = pathlib.Path(__file__).parent

with pathlib.Path("config.toml").open(mode="r") as cfg:
    config = tomlkit.load(cfg)
    ALGORITHM = config["authentication"]["algorithm"]
    ACCESS_TOKEN_EXPIRE_MINUTES = config["authentication"][
        "access_token_expire_minutes"
    ]

PKPATH = os.getenv("D3HUB_PKPATH")

try:
    with pathlib.Path(PKPATH).open(mode="rb") as sec:
        private_key_bytes = sec.read()
        PRIVATE_KEY = serialization.load_ssh_private_key(
            private_key_bytes, password=None
        )
except TypeError:
    print("You must set the D3HUB_PKPATH.")
    raise

with (CONFIG_DIR / "d3annotation.pub").open(mode="rb") as pubkey_file:
    public_key_bytes = pubkey_file.read()
    PUBLIC_KEY = serialization.load_ssh_public_key(public_key_bytes)
