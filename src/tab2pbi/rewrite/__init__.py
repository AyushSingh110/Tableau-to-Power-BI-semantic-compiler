"""Stage — translate convertible AST nodes into table-qualified DAX.

Only ``single``/``binary`` nodes with fully resolved table context are
translated. Everything else is skipped with an explicit reason.
"""
