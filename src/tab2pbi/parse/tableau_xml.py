"""Extract a .twbx archive and parse semantic metadata from its .twb XML.

Only documented Tableau XML structures are read; nothing is reverse
engineered. Every function is pure with respect to its inputs and writes
its JSON output under ``data_dir``.
"""

import json
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)


def extract_twbx(twbx_path: Path, extract_dir: Path) -> list[str]:
    """Unzip ``twbx_path`` into ``extract_dir`` and return the file list."""
    if not twbx_path.exists():
        raise FileNotFoundError(f"Workbook not found: {twbx_path}")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(twbx_path, "r") as z:
        file_list = z.namelist()
        z.extractall(extract_dir)
    log.info("Extracted %d files from %s", len(file_list), twbx_path.name)
    return file_list


def find_twb(extract_dir: Path) -> Path:
    """Locate the .twb XML file inside an extracted workbook."""
    for root_dir, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith(".twb"):
                return Path(root_dir) / f
    raise FileNotFoundError(f"No .twb file found under {extract_dir}")


def find_hyper_files(extract_dir: Path) -> list[Path]:
    """Locate all .hyper extracts inside an extracted workbook."""
    hyper_files: list[Path] = []
    for root_dir, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith(".hyper"):
                hyper_files.append(Path(root_dir) / f)
    if not hyper_files:
        raise FileNotFoundError(f"No .hyper extract found under {extract_dir}")
    return hyper_files


def parse_datasources(root: ET.Element) -> list[dict]:
    """Parse datasource fields and calculated fields from the TWB root."""
    datasource_details = []
    for ds in root.findall(".//datasource"):
        ds_name = ds.attrib.get("name", "Unnamed Datasource")
        fields, calculations = [], []
        for col in ds.findall(".//column"):
            field_name = col.attrib.get("name")
            calc = col.find("calculation")
            if calc is not None:
                calculations.append(
                    {"field_name": field_name, "formula": calc.attrib.get("formula", "")}
                )
            else:
                fields.append(
                    {
                        "field_name": field_name,
                        "role": col.attrib.get("role"),
                        "data_type": col.attrib.get("datatype"),
                    }
                )
        datasource_details.append(
            {"datasource_name": ds_name, "fields": fields, "calculations": calculations}
        )
    return datasource_details


def parse_filters_and_parameters(root: ET.Element) -> tuple[list[dict], list[dict]]:
    """Parse worksheet filters and workbook parameters."""
    filters_output = []
    for worksheet in root.findall(".//worksheet"):
        ws_name = worksheet.attrib.get("name", "Unnamed Worksheet")
        for flt in worksheet.findall(".//filter"):
            filters_output.append(
                {
                    "worksheet": ws_name,
                    "field": flt.attrib.get("field"),
                    "class": flt.attrib.get("class"),
                    "expression": flt.attrib.get("expression"),
                }
            )

    parameters_output = []
    for ds in root.findall(".//datasource"):
        if ds.attrib.get("name") == "Parameters":
            for col in ds.findall(".//column"):
                calc = col.find("calculation")
                if calc is not None:
                    parameters_output.append(
                        {
                            "parameter_name": col.attrib.get("name"),
                            "default_value": calc.attrib.get("formula"),
                        }
                    )
    return filters_output, parameters_output


def parse_field_usage(root: ET.Element) -> list[dict]:
    """Map fields/calculations referenced by each worksheet."""
    field_usage = []
    for worksheet in root.findall(".//worksheet"):
        ws_name = worksheet.attrib.get("name", "Unnamed Worksheet")
        used_fields: set[str] = set()
        for enc in worksheet.findall(".//encoding"):
            field = enc.attrib.get("field")
            if field:
                used_fields.add(field)
        for calc in worksheet.findall(".//calculation"):
            formula = calc.attrib.get("formula")
            if formula:
                used_fields.add(formula)
        field_usage.append(
            {"worksheet": ws_name, "used_fields_or_calculations": sorted(used_fields)}
        )
    return field_usage


def run(twbx_path: Path, data_dir: Path, extract_dir: Path) -> dict:
    """Execute the Tableau-XML parsing stage and write its JSON outputs.

    Returns a dict with the parsed structures and the located ``twb_path`` /
    ``hyper_files`` for downstream stages.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    extract_twbx(twbx_path, extract_dir)
    twb_path = find_twb(extract_dir)
    hyper_files = find_hyper_files(extract_dir)

    tree = ET.parse(twb_path)
    root = tree.getroot()

    datasources = parse_datasources(root)
    filters, parameters = parse_filters_and_parameters(root)
    field_usage = parse_field_usage(root)

    _write(data_dir / "parsed_tableau_schema.json", datasources)
    _write(data_dir / "parsed_tableau_filters.json", filters)
    _write(data_dir / "parsed_tableau_parameters.json", parameters)
    _write(data_dir / "parsed_tableau_field_usage.json", field_usage)

    total_fields = sum(len(ds["fields"]) for ds in datasources)
    total_calcs = sum(len(ds["calculations"]) for ds in datasources)
    log.info(
        "Parsed TWB: %d datasources, %d fields, %d calculations, %d filters, %d parameters",
        len(datasources),
        total_fields,
        total_calcs,
        len(filters),
        len(parameters),
    )
    return {
        "twb_path": twb_path,
        "hyper_files": hyper_files,
        "datasources": datasources,
    }


def _write(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4)
