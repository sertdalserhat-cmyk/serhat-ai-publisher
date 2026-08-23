import pytest

from src.vocab import CLAIM_TYPES, PLATFORM_REPORTED_COUNT, require_claim_type


def test_t06_unknown_claim_type_is_rejected_with_valid_types():
    with pytest.raises(ValueError) as error:
        require_claim_type("MADE_UP_METRIC")
    assert "AMZ_BSR" in str(error.value)
    assert "Geçerli tipler" in str(error.value)


def test_platform_reported_count_semantics_are_exactly_the_frozen_five():
    marked = {name for name, spec in CLAIM_TYPES.items() if spec.semantics == PLATFORM_REPORTED_COUNT}
    assert marked == {
        "AMZ_SEARCH_RESULT_COUNT", "ETSY_LISTING_COUNT", "YT_RESULT_COUNT",
        "GB_TITLE_COUNT", "OL_SUBJECT_WORK_COUNT",
    }
