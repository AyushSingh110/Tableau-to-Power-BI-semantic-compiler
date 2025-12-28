# Tableau → Power BI Semantic Compiler

A research-grade semantic compilation pipeline for transforming Tableau analytical semantics into Power BI Tabular Object Model (TOM) with full traceability and engine-aware translation.

## Overview

This project implements a **semantic compiler** that translates Tableau workbooks into Power BI semantic models by preserving analytical intent rather than visual layout. Unlike traditional migration tools that focus on dashboard recreation, this compiler treats both platforms as analytical execution engines and ensures **engine-safe, explainable, and auditable** transformations.

### What This Project Is

- **Semantic Analysis & Compilation**: Canonical intermediate representation bridging Tableau and Power BI
- **Engine-Aware Translation**: Respects differences between Tableau's query engine and Power BI's VertiPaq/DAX
- **Data-Driven Validation**: Uses actual data patterns instead of metadata assumptions
- **Research-Grade Pipeline**: Deterministic, explainable, and fully documented transformations

### What This Project Is Not

- ❌ Visual migration tool (dashboards, formatting, layouts)
- ❌ File-level converter (.twbx → .pbix)
- ❌ Heuristic-based "best guess" translator
- ❌ Silent converter that drops unsupported features

---

## Project Objectives

The compiler is designed to:

1. **Extract Tableau semantics** using official and documented APIs only
2. **Preserve analytical intent** across different execution engines
3. **Avoid speculative conversion** of joins, measures, or business logic
4. **Produce valid Power BI TOM** compatible with Tabular Editor and Power BI Desktop
5. **Explicitly report** unsupported, unsafe, or ambiguous conversions

---

## Architecture

The pipeline consists of 11 deterministic stages, each producing auditable intermediate outputs:

```
.twbx Archive
    ↓
[1] Tableau XML Parsing
    ↓
[2] Hyper Extract Access
    ↓
[3] Logical-Physical Mapping
    ↓
[4] Canonical Semantic Model
    ↓
[5] Calculation Classification
    ↓
[6] Safe DAX Rewriting
    ↓
[7] Relationship Extraction
    ↓
[8] Data-Driven Inference
    ↓
[9] Table Context Resolution
    ↓
[10] Power BI Semantic Model
    ↓
[11] TOM Export
    ↓
.bim / Power BI TOM
```

---

## Pipeline Stages

### Stage 1: Tableau XML Parsing

**Purpose**: Extract semantic metadata from Tableau workbooks

**Input**: `.twb` files (extracted from `.twbx` archives)

**Output**: `data/parsed_*.json`

**Extracts**:
- Datasources and connections
- Dimensions and measures
- Calculated fields and parameters
- Filters and field-to-worksheet mappings

**Implementation**: `parsing_tableau.py`

**Guarantees**: Uses only documented Tableau XML structures—no reverse engineering

---

### Stage 2: Hyper Extract Access

**Purpose**: Access Tableau's proprietary data storage using official APIs

**Input**: `.hyper` files from `.twbx` archives

**Output**: 
- `parsed_hyper_schema.json` (table schemas, column types)
- `hyper_raw_data.csv` (sampled data for validation)

**API**: Tableau Hyper API (official, supported)

**Usage**: Validation and data-driven inference only—not for bulk data migration

---

### Stage 3: Logical-Physical Mapping

**Purpose**: Map Tableau's logical field identifiers to Hyper physical columns

**Input**: Parsed Tableau metadata + Hyper schema

**Output**: `logical_physical_mapping.json`

**Guarantees**:
- Deterministic one-to-one mapping
- No duplicate or ambiguous ownership
- No inferred aliases or heuristic matching

---

### Stage 4: Canonical Semantic Model

**Purpose**: Construct a tool-agnostic intermediate representation (IR)

**Output**: `canonical_powerbi_model.json`

**Components**:
- **Tables**: Physical data containers
- **Columns**: Typed fields with lineage
- **Measures**: Analytical expressions
- **Relationships**: Foreign key constraints

**Role**: Decouples Tableau semantics from Power BI syntax, enabling independent validation and transformation

---

### Stage 5: Calculation Classification

**Purpose**: Analyze and categorize Tableau calculated fields by convertibility

**Output**: `calculation_classification.json`

**Categories**:
- ✅ **Directly Convertible**: Simple aggregations, arithmetic expressions
- ⚠️ **Requires Redesign**: Complex logic needing DAX-specific patterns
- ❌ **Unsupported**: LOD expressions, table calculations, window functions

**Policy**: No silent drops—all skipped measures are documented with justification

**Implementation**: `calculation_classification.py`

---

### Stage 6: Safe DAX Rewriting

**Purpose**: Convert only engine-safe Tableau expressions to DAX

**Output**: `converted_dax_measures.json`

**Converts**:
- Simple aggregations (`SUM`, `AVG`, `COUNT`, etc.)
- Algebraic combinations of aggregations
- Basic conditional logic

**Explicitly Skips**:
- Level of Detail (LOD) expressions
- Table calculations (`RUNNING_SUM`, `INDEX`, etc.)
- Window functions (`WINDOW_AVG`, `LOOKUP`, etc.)

**Implementation**: `rewrite_convertible_calculations.py`

---

### Stage 7: Relationship Extraction

**Purpose**: Detect Tableau's data modeling strategy

**Output**: `relationships_from_twb.json`

**Detects**:
- **Logical Relationships**: Tableau's modern relationship model
- **Physical Joins**: Legacy join-based data sources

**Policy**: Does not infer or guess join keys—preserves ambiguity when Tableau defers resolution to query time

**Implementation**: `extract_relationships_from_twb.py`

---

### Stage 8: Data-Driven Relationship Inference

**Purpose**: Infer foreign key relationships using actual data patterns

**Output**: `inferred_powerbi_relationships.json`

**Methods**:
- **Primary Key Detection**: Uniqueness and non-nullability analysis
- **Foreign Key Detection**: Referential integrity validation
- **Confidence Scoring**: Coverage-based relationship strength

**Guarantees**: Relationships emitted only when confidence thresholds are met

---

### Stage 9: Table Context Resolution

**Purpose**: Resolve measure ownership for valid DAX placement

**Output**: `semantic_model_with_context.json`

**Required For**:
- Valid DAX measure definitions
- Power BI engine execution
- Prevention of ambiguous or floating measures

---

### Stage 10: Final Power BI Semantic Model

**Purpose**: Merge all semantic components into unified model

**Output**: `final_powerbi_semantic_model.json`

**Includes**:
- Canonical semantic model
- Converted DAX measures
- Validated relationships
- Full conversion report with audit trail

---

### Stage 11: Tabular Object Model (TOM) Export

**Purpose**: Generate Power BI-compatible model definition

**Output**: `powerbi_tom_model.json`

**Compatible With**:
- Tabular Editor 2/3
- Power BI Desktop (import mode)
- Azure Analysis Services

**Features**:
- Standards-compliant TOM JSON
- Annotations documenting conversion decisions
- Preserved metadata for unsupported features

---

## Core Design Principles

| Principle | Description |
|-----------|-------------|
| **Engine Correctness > Visual Parity** | Prioritizes executable semantics over UI recreation |
| **Explicit Uncertainty > Silent Failure** | Reports ambiguities rather than making assumptions |
| **Data-Driven Validation > Metadata Trust** | Validates using actual data patterns |
| **Semantic Intent > Syntactic Conversion** | Preserves analytical meaning across different syntaxes |
| **Official APIs Only** | No reverse engineering or undocumented features |

---

## Installation

### Prerequisites

- Python 3.8+
- Tableau Hyper API
- Access to Tableau `.twbx` or `.twb` files

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/tableau-powerbi-compiler.git
cd tableau-powerbi-compiler

# Install dependencies
pip install tableauhyperapi
pip install -r requirements.txt

# Extract .twbx archive
unzip your_workbook.twbx -d extracted/
```

---

## Usage

### Basic Workflow

```bash
# 1. Parse Tableau workbook
python parsing_tableau.py extracted/workbook.twb

# 2. Extract Hyper data
python extract_hyper.py extracted/Data/Extracts/extract.hyper

# 3. Run full compilation pipeline
python run_pipeline.py extracted/

# 4. Output generated at:
# - final_powerbi_semantic_model.json
# - powerbi_tom_model.json
```

### Import into Power BI

```bash
# Option 1: Use Tabular Editor
# Open powerbi_tom_model.json in Tabular Editor

# Option 2: Use Power BI Desktop
# File → Import → Import from Analysis Services
```

---

## Output Files

| File | Description |
|------|-------------|
| `parsed_*.json` | Raw Tableau metadata extraction |
| `logical_physical_mapping.json` | Field identifier resolution |
| `canonical_powerbi_model.json` | Tool-agnostic semantic IR |
| `calculation_classification.json` | Measure convertibility analysis |
| `converted_dax_measures.json` | Successfully translated DAX |
| `relationships_from_twb.json` | Extracted relationship metadata |
| `inferred_powerbi_relationships.json` | Data-driven relationship evidence |
| `semantic_model_with_context.json` | Context-resolved semantic model |
| `final_powerbi_semantic_model.json` | Complete Power BI model with audit trail |
| `powerbi_tom_model.json` | Power BI TOM export |

---

## Known Limitations

### Tableau Features Not Supported

- **Level of Detail (LOD) Expressions**: Require manual DAX redesign
- **Table Calculations**: Context-dependent logic incompatible with DAX
- **Window Functions**: No direct DAX equivalent
- **Custom SQL**: Cannot be translated without database access
- **Blended Data Sources**: Multi-source queries need redesign

### Power BI Constraints

- **DirectQuery Limitations**: Some DAX patterns only work in Import mode
- **Relationship Cardinality**: Must be explicitly defined (no Tableau-style deferred joins)
- **Calculation Groups**: Advanced time intelligence may need manual implementation

---

## Conversion Report

Each compilation produces a detailed audit trail:

```json
{
  "total_measures": 45,
  "converted_measures": 32,
  "skipped_measures": 13,
  "skipped_reasons": {
    "LOD_expression": 8,
    "table_calculation": 3,
    "window_function": 2
  },
  "relationships_inferred": 12,
  "relationships_confidence_low": 2
}
```

---

## Contributing

This is a research-oriented project. Contributions should:

1. Maintain deterministic behavior
2. Use only official APIs
3. Include comprehensive documentation
4. Provide test cases with sample workbooks

---

## Acknowledgments

- Tableau Hyper API documentation
- Power BI Tabular Object Model (TOM) specification
- DAX language reference

---

## Support

For issues, questions, or feature requests, please open a GitHub issue with:
- Sample Tableau workbook (anonymized if needed)
- Expected behavior
- Actual output and conversion report

---

## Roadmap

- [ ] Advanced DAX pattern library for complex Tableau calculations
- [ ] Incremental refresh configuration mapping
- [ ] Row-level security (RLS) translation
- [ ] Tableau extract → Power BI dataset automation
- [ ] Validation suite with reference workbooks
