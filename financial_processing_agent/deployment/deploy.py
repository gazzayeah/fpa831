"""
Agent Engine create / update / delete for the AP assistant.

Eval and CLI stay on ``Workflow`` (no model). This module pickles the ADK
``root_agent`` (gather then recommend) onto Vertex Agent Engine. Posting is
still not on that graph — ``submit_finance_decision`` stays approval-gated
in ``Workflow.approve``.

Stage extra packages under ``.agent_engine_src/`` (gitignored) so the remote
container gets ``financial_processing_agent`` plus bundled corpus and fixtures.
Do not tar the repo ``.venv``.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from importlib.metadata import version
from pathlib import Path
from typing import Any

from financial_processing_agent.agent import root_agent
from financial_processing_agent.shared_libraries.settings import settings

AGENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = AGENT_DIR.parent
STAGE_DIRNAME = ".agent_engine_src"
_COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".env",
    "*.sqlite",
    "bundled_corpus",
    "bundled_fixtures",
)

# Remote runtime install list. cloudpickle + pydantic must be top-level: Agent
# Engine pickles AdkApp locally and unpickles in the container.
REQUIREMENTS = [
    "google-adk",
    "google-cloud-aiplatform[adk,agent_engines]",
    "cloudpickle",
    "pydantic",
    "pydantic-settings",
]

ENGINE_SPEC: dict[str, Any] = {
    "display_name": "fpa831-agent-dev",
    "description": (
        "Accounts-payable assistant: retrieve policy, reconcile in code, "
        "recommend. Posting is not performed on this graph."
    ),
    "min_instances": 0,
    "max_instances": 1,
    "resource_limits": {"cpu": "1", "memory": "2Gi"},
    "container_concurrency": 9,
    "python_version": "3.12",
}

_ENGINE_RESOURCE_RE = re.compile(
    r"^projects/[^/]+/locations/[^/]+/reasoningEngines/[0-9]+$"
)

# Agent Engine injects these; putting them in spec.deployment_spec.env is
# FAILED_PRECONDITION ("Environment variable name 'X' is reserved").
RESERVED_ENGINE_ENV = frozenset(
    {
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_QUOTA_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "PORT",
        "K_SERVICE",
        "K_REVISION",
        "K_CONFIGURATION",
        "GOOGLE_APPLICATION_CREDENTIALS",
    }
)


def stage_extra_packages(dest: Path | None = None) -> Path:
    """Copy importable sources into a tree that does not include .venv or .env.

    Agent Engine tars extra_packages by path. Cwd is later the stage so tar
    members are top-level ``financial_processing_agent/``. Corpus and fixtures
    are copied *into* that package as ``bundled_corpus`` / ``bundled_fixtures``
    so remote ``settings`` can find them without the git repo layout.
    """
    if root_agent is None:
        raise RuntimeError(
            "google-adk is not installed; sync with --extra deploy before apply"
        )
    stage = dest or (AGENT_DIR / STAGE_DIRNAME)
    stage.mkdir(parents=True, exist_ok=True)
    package_src = AGENT_DIR / "financial_processing_agent"
    target = stage / "financial_processing_agent"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(package_src, target, ignore=_COPY_IGNORE)

    corpus_src = settings.resolved_corpus_dir
    corpus_dest = target / "bundled_corpus"
    if corpus_dest.exists():
        shutil.rmtree(corpus_dest)
    shutil.copytree(corpus_src, corpus_dest, ignore=_COPY_IGNORE)

    fixtures_src = settings.resolved_fixtures_dir
    fixtures_dest = target / "bundled_fixtures"
    if fixtures_dest.exists():
        shutil.rmtree(fixtures_dest)
    shutil.copytree(fixtures_src, fixtures_dest, ignore=_COPY_IGNORE)
    return stage


def extra_package_names() -> list[str]:
    """Top-level directory names inside the stage (import path on the engine)."""
    return ["financial_processing_agent"]


def _requirements() -> list[str]:
    """Pin cloudpickle and pydantic to the versions used to pickle AdkApp."""
    skip = {"cloudpickle", "pydantic"}
    base = [item for item in REQUIREMENTS if item.split("[", 1)[0] not in skip]
    return [
        *base,
        f"cloudpickle=={version('cloudpickle')}",
        f"pydantic=={version('pydantic')}",
    ]


def _app():
    """Wrap root_agent for Agent Engine. Tracing on; no Memory Bank schema."""
    from vertexai.preview.reasoning_engines import AdkApp

    return AdkApp(agent=root_agent, enable_tracing=True)


def _env() -> dict[str, str]:
    """Remote process env. Must not include RESERVED_ENGINE_ENV names.

    Agent Engine already injects GOOGLE_CLOUD_PROJECT and
    GOOGLE_CLOUD_LOCATION. Settings reads GCP_PROJECT_ID / GCP_LOCATION.
    Corpus and fixtures come from bundled dirs, not these vars.
    """
    env = {
        "GCP_PROJECT_ID": settings.gcp_project_id,
        "GCP_LOCATION": settings.gcp_location,
        "GOOGLE_GENAI_USE_VERTEXAI": "true",
        "AGENT_MODEL": settings.agent_model,
    }
    reserved = RESERVED_ENGINE_ENV.intersection(env)
    if reserved:
        raise ValueError(
            "Agent Engine reserved env names cannot be in spec.deployment_spec.env: "
            + ", ".join(sorted(reserved))
        )
    return env


def _staging_uri() -> str:
    """gs:// bucket Terraform creates for Agent Engine package upload."""
    return f"gs://{settings.agent_staging_bucket}"


def _engine_config() -> dict[str, Any]:
    """Build create/update config. Cwd becomes the stage so tar members are correct."""
    stage = stage_extra_packages()
    os.chdir(stage)
    return {
        **ENGINE_SPEC,
        "requirements": _requirements(),
        "extra_packages": extra_package_names(),
        "env_vars": _env(),
        "service_account": settings.runtime_service_account,
        "staging_bucket": _staging_uri(),
    }


def _client():
    import vertexai

    vertexai.init(
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        staging_bucket=_staging_uri(),
    )
    return vertexai.Client(
        project=settings.gcp_project_id,
        location=settings.gcp_location,
    )


def _resource_name(remote: Any) -> str:
    """Extract projects/.../reasoningEngines/ID from a create/update response."""
    name = getattr(remote, "resource_name", None)
    if name:
        return str(name)
    api = getattr(remote, "api_resource", None)
    if api is not None and getattr(api, "name", None):
        return str(api.name)
    raise RuntimeError("Agent Engine resource name missing")


def _print_resource(name: str) -> None:
    print(f"AGENT_ENGINE_RESOURCE={name}")


def normalize_engine_resource(
    resource: str,
    *,
    project: str | None = None,
    location: str | None = None,
) -> str:
    """Expand a bare engine id so PATCH hits reasoningEngines/, not HTML 404.

    google-genai only prefixes ``projects/{project}/locations/{location}/``
    when the name does not already start with ``projects/``. A numeric id
    becomes ``.../locations/us-central1/<id>``, which Google's frontend
    returns as the robot HTML 404 page instead of a Vertex JSON error.
    """
    name = resource.strip().strip("\"'`")
    if not name:
        return ""
    if _ENGINE_RESOURCE_RE.match(name):
        return name
    project = project or settings.gcp_project_id
    location = location or settings.gcp_location
    engine_id = name
    if name.startswith("reasoningEngines/"):
        engine_id = name.split("/", 1)[1]
    if engine_id.isdigit():
        return f"projects/{project}/locations/{location}/reasoningEngines/{engine_id}"
    raise ValueError(
        "Agent Engine resource must be "
        "projects/<project>/locations/<location>/reasoningEngines/<id> "
        f"(or the numeric id). Got {resource!r}."
    )


def _lookup_by_display_name() -> str:
    """Find an existing engine with ENGINE_SPEC display_name, or return empty."""
    target = ENGINE_SPEC["display_name"]
    try:
        client = _client()
        engines = client.agent_engines.list()
    except Exception as exc:
        print(f"Could not list Agent Engines ({exc}); create if no resource", flush=True)
        return ""
    for engine in engines:
        api = getattr(engine, "api_resource", None)
        display = getattr(engine, "display_name", None) or getattr(api, "display_name", "")
        if display == target:
            return _resource_name(engine)
    return ""


def apply(resource: str = "") -> str:
    """Create when resource is empty (or look up by display name); update otherwise."""
    client = _client()
    config = _engine_config()
    app = _app()
    name = normalize_engine_resource(resource)
    if not name:
        name = normalize_engine_resource(os.environ.get("AGENT_ENGINE_RESOURCE", ""))
    if not name:
        name = _lookup_by_display_name()
    if name:
        print(f"Updating {name}", flush=True)
        remote = client.agent_engines.update(name=name, agent=app, config=config)
    else:
        print("Creating Agent Engine", flush=True)
        remote = client.agent_engines.create(agent=app, config=config)
    deployed = _resource_name(remote)
    _print_resource(deployed)
    return deployed


def main() -> None:
    """CLI: --apply (CI), --create, --update, --delete."""
    parser = argparse.ArgumentParser(description="fpa831 Agent Engine deploy")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true")
    group.add_argument("--update", metavar="RESOURCE")
    group.add_argument("--delete", metavar="RESOURCE")
    group.add_argument(
        "--apply",
        action="store_true",
        help="Create if --resource is empty (after display-name lookup), otherwise update",
    )
    parser.add_argument(
        "--resource",
        default="",
        help="Reasoning engine resource name for --apply (empty = lookup or create)",
    )
    args = parser.parse_args()

    if args.apply:
        apply(args.resource)
        return

    client = _client()
    config = _engine_config()
    app = _app()
    if args.create:
        remote = client.agent_engines.create(agent=app, config=config)
        _print_resource(_resource_name(remote))
        return
    if args.update:
        name = normalize_engine_resource(args.update)
        print(f"Updating {name}", flush=True)
        remote = client.agent_engines.update(name=name, agent=app, config=config)
        _print_resource(_resource_name(remote))
        return
    name = normalize_engine_resource(args.delete)
    client.agent_engines.delete(name=name, force=True)
    print(f"deleted {name}")


if __name__ == "__main__":
    main()
