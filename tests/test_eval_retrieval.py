import pytest

from inspection_copilot.eval_retrieval import (
    Question,
    first_relevant_rank,
    is_relevant,
    load_questions,
    summarise,
)

Q = Question(
    id="t1",
    category="lexical",
    source_key="tm5_684",
    page=22,
    question="?",
    evidence="cracked ones sound dull and hollow",
    answer="",
)


def test_relevance_ignores_case_and_broken_whitespace() -> None:
    assert is_relevant(Q, "tm5_684", "...Cracked  ones sou nd dull\nand hollow.")


def test_relevance_requires_the_right_document() -> None:
    assert not is_relevant(Q, "fist4_1b", "cracked ones sound dull and hollow")


def test_first_relevant_rank() -> None:
    hits = [("tm5_684", "other text"), ("tm5_684", "cracked ones sound dull and hollow")]
    assert first_relevant_rank(Q, hits) == 2
    assert first_relevant_rank(Q, hits[:1]) is None


def test_summarise() -> None:
    m = summarise([1, 3, None, 10])
    assert m["hit@1"] == 0.25
    assert m["hit@3"] == 0.5
    assert m["hit@5"] == 0.5
    assert m["mrr@10"] == pytest.approx((1 + 1 / 3 + 0 + 1 / 10) / 4)


def test_question_set_is_well_formed() -> None:
    questions = load_questions()
    assert len({q.id for q in questions}) == len(questions)
    assert {q.category for q in questions} == {"lexical", "paraphrase"}
    assert all(q.evidence and q.answer for q in questions)
