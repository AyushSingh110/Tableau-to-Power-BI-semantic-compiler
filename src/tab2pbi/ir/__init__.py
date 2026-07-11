"""Canonical intermediate representation (IR).

Submodules:
- ``semantic_model`` : build the AST-shaped semantic model from parsed inputs
  (the step that was previously missing).
- ``context``        : resolve measure table ownership and table-qualified DAX.
- ``canonical``      : assemble the tool-agnostic canonical model.
- ``finalize``       : merge measures + audit report into the final model.
"""
