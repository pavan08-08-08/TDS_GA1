import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def as_bool(value):
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "true", "1", "yes", "on"
    }


def normalize(key, value):
    if key in {"port", "workers"}:
        return int(value)

    if key == "debug":
        return as_bool(value)

    return str(value)


def load_config():
    # 1. Hardcoded defaults
    config = DEFAULTS.copy()

    # 2. Environment-specific YAML
    yaml_path = Path("config.development.yaml")

    if yaml_path.exists():
        with yaml_path.open() as file:
            yaml_config = yaml.safe_load(file) or {}

        config.update(yaml_config)

    # 3. .env file
    env_file = dotenv_values(".env")

    for key, value in env_file.items():
        if value is None:
            continue

        if key.startswith("APP_"):
            config_key = key[4:].lower()
            config[config_key] = value

        elif key == "NUM_WORKERS":
            config["workers"] = value

        elif key in config:
            config[key] = value

    # 4. Operating system environment variables
    for key, value in os.environ.items():
        if not key.startswith("APP_"):
            continue

        config_key = key[4:].lower()

        if config_key in config:
            config[config_key] = value

    # Normalize types
    for key in config:
        config[key] = normalize(key, config[key])

    return config


@app.get("/effective-config")
def effective_config(
    set: list[str] = Query(default=[])
):
    config = load_config()

    # 5. CLI-style query overrides
    for override in set:
        if "=" not in override:
            continue

        key, value = override.split("=", 1)
        key = key.strip().lower()

        if key in config:
            config[key] = normalize(key, value)

    # Never expose the actual secret
    config["api_key"] = "****"

    return config


@app.get("/")
def root():
    return {"status": "ok", "endpoint": "/effective-config"}


@app.get("/health")
def health():
    return {"status": "healthy"}