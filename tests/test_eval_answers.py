"""Deterministic checks of the answer-quality evaluation (no API calls)."""

from inspection_copilot.eval_answers import cited_ids, evidence_in, mean_ci, numbers_match

SOURCES = [
    {"id": "S1", "text": "Cracked ones sound dull and hollow when tapped."},
    {"id": "S2", "text": "Wood poles are inspected for decay."},
]


def test_numbers_match_oracle_and_null() -> None:
    assert numbers_match("Inspections 3 and 11 tie with 7 insulators each.", [3, 11, 7])
    assert not numbers_match("", [3, 11, 7])  # null answer fails
    assert not numbers_match("Inspection 3 has 7 insulators.", [3, 11, 7])  # misses the tie


def test_numbers_match_accepts_unit_variants_but_not_wrong_values() -> None:
    assert numbers_match("Escalated runs take about 0.93 s on average.", [933])
    assert numbers_match("about 933 ms", [933])
    assert numbers_match("The highest confidence is 73%.", [0.73])
    assert numbers_match("1,135 ms", [1135])
    assert not numbers_match("about 500 ms", [933])
    assert not numbers_match("16 inspections", [15])  # small counts must be exact


def test_evidence_cited_requires_the_cited_passage() -> None:
    answer = "Tap it; a cracked one sounds dull [S1]."
    assert cited_ids(answer) == {"S1"}
    assert evidence_in(SOURCES, "cracked ones sound dull and hollow", only=cited_ids(answer))
    assert not evidence_in(SOURCES, "cracked ones sound dull and hollow", only={"S2"})
    assert evidence_in(SOURCES, "CRACKED ones  sound dull and hollow")  # case/space-insensitive


def test_mean_ci() -> None:
    m, ci = mean_ci([1.0, 0.0, 1.0, 1.0])
    assert m == 0.75 and 0 < ci < 1
