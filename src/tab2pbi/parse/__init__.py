"""Stage 1 — extraction and parsing of the Tableau workbook.

Submodules:
- ``tableau_xml`` : unzip the .twbx and parse the .twb XML (fields, calcs,
  filters, parameters, field usage).
- ``hyper``       : read the .hyper extract schema and sample its data.
- ``mapping``     : map Tableau logical fields to Hyper physical columns.
"""
