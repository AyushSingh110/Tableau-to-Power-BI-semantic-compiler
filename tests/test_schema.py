"""The golden run's artifacts must conform to the versioned IR schemas."""

import pytest

from tab2pbi.ir.validate import SchemaValidationError, validate


def test_semantic_model_conforms(superstore_artifacts):
    validate(superstore_artifacts["semantic"], "semantic_model")


def test_final_model_conforms(superstore_artifacts):
    validate(superstore_artifacts["final"], "final_model")


def test_schema_rejects_bad_input():
    with pytest.raises(SchemaValidationError):
        validate({"tables": {}}, "final_model")  # missing required keys
