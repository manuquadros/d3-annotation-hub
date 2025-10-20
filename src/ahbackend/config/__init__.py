"""Load configuration files and set global variables."""

import os
import pathlib

import tomlkit

CONFIG_DIR = pathlib.Path(__file__).parent

with pathlib.Path("config.toml").open(mode="r") as cfg:
    config = tomlkit.load(cfg)
    ALGORITHM = config["authentication"]["algorithm"]
    ACCESS_TOKEN_EXPIRE_MINUTES = config["authentication"][
        "access_token_expire_minutes"
    ]

PKPATH = os.getenv("D3HUB_PKPATH")

try:
    with pathlib.Path(PKPATH).open(mode="r") as sec:
        PRIVATE_KEY = sec.read()
except TypeError:
    print("You must set the D3HUB_PKPATH.")

with (CONFIG_DIR / "d3annotation.pub").open(mode="r") as pubkey_file:
    PUBLIC_KEY = pubkey_file.read()
