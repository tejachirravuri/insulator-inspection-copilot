from inspection_copilot.retrieval import reciprocal_rank_fusion


def test_item_ranked_well_in_both_lists_wins() -> None:
    vector = [1, 2, 3]
    keyword = [2, 4, 1]
    fused = [item for item, _ in reciprocal_rank_fusion([vector, keyword])]
    # 2 is rank 2 + rank 1, 1 is rank 1 + rank 3: 2 has the higher sum of 1/(60+rank).
    assert fused[:2] == [2, 1]
    assert set(fused) == {1, 2, 3, 4}


def test_item_in_one_list_only_still_appears() -> None:
    fused = dict(reciprocal_rank_fusion([[7], []]))
    assert fused == {7: 1 / 61}


def test_ties_are_deterministic() -> None:
    assert reciprocal_rank_fusion([[5], [3]]) == [(3, 1 / 61), (5, 1 / 61)]
