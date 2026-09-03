"""
Typed configuration that must stay outside orchestration.

``settings`` is loaded from environment variables and an optional ``.env``
file. Do not hard-code model names or paths in ``workflow.py`` or tools.
Override ``corpus_dir``, ``fixtures_dir``, or ``run_store_path`` in tests.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime knobs for GCP, the LLM, tool budgets, and fixture locations."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gcp_project_id: str = "light-operator-364723"
    gcp_location: str = "us-central1"
    google_genai_use_vertexai: bool = True
    agent_model: str = "gemini-2.5-flash"
    max_tool_calls: int = 12
    max_steps: int = 20
    tool_timeout_seconds: float = 8.0
    run_store_path: str = ""
    corpus_dir: str = ""
    fixtures_dir: str = ""

    @property
    def package_root(self) -> Path:
        """Directory containing this Python package (inner financial_processing_agent/)."""
        return Path(__file__).resolve().parents[1]

    @property
    def repo_root(self) -> Path:
        """Git repository root (fpa831/), four levels above this file."""
        return Path(__file__).resolve().parents[3]

    @property
    def resolved_corpus_dir(self) -> Path:
        """Policy markdown corpus used by retrieve_finance_documents."""
        if self.corpus_dir:
            return Path(self.corpus_dir)
        return self.repo_root / "docs" / "finance_rag_corpus"

    @property
    def resolved_fixtures_dir(self) -> Path:
        """JSON fixtures for vendor, PO, invoice history, and FIN-00x cases."""
        if self.fixtures_dir:
            return Path(self.fixtures_dir)
        return self.package_root.parent / "fixtures"

    @property
    def resolved_run_store_path(self) -> Path:
        """SQLite file for run persistence and approval replay."""
        if self.run_store_path:
            return Path(self.run_store_path)
        return self.package_root.parent / ".local" / "runs.sqlite"


# Process-wide singleton. Tests override paths via env vars or a custom Settings().
settings = Settings()
