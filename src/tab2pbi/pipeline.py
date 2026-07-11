"""End-to-end pipeline orchestration.

Runs every stage in dependency order and returns a summary suitable for a
console report. Each stage writes its JSON artifact under ``data_dir`` and
passes its in-memory result to the next stage, so the chain is explicit.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .classify import classifier
from .export import tabular_editor, tom
from .ir import canonical, context, finalize, semantic_model
from .logging_config import get_logger
from .parse import hyper, mapping, tableau_xml
from .relationships import from_hyper, from_twb
from .rewrite import dax

log = get_logger(__name__)


@dataclass
class PipelineResult:
    twbx_path: Path
    data_dir: Path
    tables: dict = field(default_factory=dict)
    final_model: dict = field(default_factory=dict)
    tom: dict = field(default_factory=dict)

    @property
    def report(self) -> dict:
        return self.final_model.get("conversion_report", {})


def run(
    twbx_path: Path,
    data_dir: Path,
    extract_dir: Path | None = None,
    fact_table: str | None = None,
) -> PipelineResult:
    """Execute the full Tableau → Power BI TOM pipeline."""
    twbx_path = Path(twbx_path)
    data_dir = Path(data_dir)
    extract_dir = Path(extract_dir) if extract_dir else data_dir / "twbx_extracted"
    data_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== tab2pbi pipeline: %s ===", twbx_path)

    # 1. Parse Tableau XML + Hyper extract + logical/physical mapping.
    parsed = tableau_xml.run(twbx_path, data_dir, extract_dir)
    hyper_result = hyper.run(parsed["hyper_files"][0], data_dir)
    schema = hyper_result["schema"]
    mappings = mapping.run(parsed["datasources"], schema, data_dir)

    # 2. Build the AST-shaped semantic model.
    sm = semantic_model.run(parsed["datasources"], schema, data_dir, fact_table=fact_table)

    # 3. Relationships (declared + data-driven).
    from_twb.run(parsed["twb_path"], data_dir)
    inferred = from_hyper.run(schema, hyper_result["tables_dir"], data_dir)

    # 4. Resolve table context (ownership + table-qualified DAX).
    ctx = context.run(sm, mappings, data_dir)

    # 5. Classify + rewrite (both AST-driven).
    classification = classifier.run(ctx, data_dir)
    converted = dax.run(ctx, data_dir)

    # 6. Assemble canonical + final models.
    canon = canonical.run(schema, ctx, inferred, data_dir)
    final_model = finalize.run(canon, ctx, converted, classification, data_dir)

    # 7. Export TOM + Tabular Editor model.
    tom_model = tom.run(final_model, schema, data_dir)
    tabular_editor.run(tom_model, data_dir)

    log.info("=== pipeline complete ===")
    return PipelineResult(
        twbx_path=twbx_path,
        data_dir=data_dir,
        tables=final_model["tables"],
        final_model=final_model,
        tom=tom_model,
    )
