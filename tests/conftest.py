"""Shared pytest fixtures.

The golden end-to-end fixture runs the full pipeline once against the bundled
Superstore workbook into a temporary directory, so tests can assert on real
artifacts without polluting the repo's ``data/`` directory.
"""

import json
from pathlib import Path

import pytest

from tab2pbi import pipeline

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPERSTORE = REPO_ROOT / "examples" / "Superstore.twbx"


@pytest.fixture(scope="session")
def superstore_run(tmp_path_factory):
    """Run the whole pipeline on Superstore into a temp dir (once per session)."""
    if not SUPERSTORE.exists():
        pytest.skip(f"sample workbook missing: {SUPERSTORE}")
    data_dir = tmp_path_factory.mktemp("tab2pbi_data")
    result = pipeline.run(twbx_path=SUPERSTORE, data_dir=data_dir)
    return result


@pytest.fixture(scope="session")
def superstore_artifacts(superstore_run):
    """Load the key JSON artifacts produced by the golden run."""
    data_dir = superstore_run.data_dir

    def load(name):
        return json.loads((data_dir / name).read_text(encoding="utf-8"))

    return {
        "final": load("final_powerbi_semantic_model.json"),
        "tom": load("powerbi_tom_model.json"),
        "converted": load("converted_dax_measures.json"),
        "inferred": load("inferred_powerbi_relationships.json"),
        "semantic": load("semantic_model.json"),
    }
