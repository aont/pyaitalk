"""Configuration loader for pyaitalk."""

from __future__ import annotations

import os
import tomllib
import warnings

DEFAULT_CONFIG_PATH = "config.toml"
CONFIG_ENV_VAR = "PYAITALK_CONFIG"


def load_config(config_path: str | None = None) -> dict:
    path = config_path or os.environ.get(CONFIG_ENV_VAR) or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def resolve_aitalk_path(config_path: str | None = None) -> str:
    cfg = load_config(config_path)
    path = cfg.get("aitalk_path")
    if path:
        return path
    env_path = os.environ.get("AITALK_PATH")
    if env_path:
        warnings.warn(
            "AITALK_PATH is deprecated. Set aitalk_path in config.toml instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return env_path
    raise ValueError("aitalk_path is required in config.toml")


def resolve_auth_code(args_auth_code: str | None = None, config_path: str | None = None) -> str:
    if args_auth_code:
        warnings.warn(
            "--auth-code is deprecated. Set aitalk_authcode in config.toml instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return args_auth_code

    cfg = load_config(config_path)
    auth_code = cfg.get("aitalk_authcode")
    if auth_code:
        return auth_code

    env_auth = os.environ.get("AITALK_AUTHCODE")
    if env_auth:
        warnings.warn(
            "AITALK_AUTHCODE is deprecated. Set aitalk_authcode in config.toml instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return env_auth
    raise ValueError("aitalk_authcode is required in config.toml")
