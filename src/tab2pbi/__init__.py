"""tab2pbi — deterministic Tableau → Power BI semantic compiler.

The package translates a Tableau workbook (.twbx) into a Power BI Tabular
Object Model (TOM) via a canonical semantic intermediate representation (IR).
It is deterministic and never guesses: any calculation it cannot translate is
recorded as unsupported, with a reason.
"""

__version__ = "0.1.0"
