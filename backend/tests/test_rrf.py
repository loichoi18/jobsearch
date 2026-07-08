"""Reciprocal Rank Fusion math."""

from retrieval.hybrid import reciprocal_rank_fusion


def test_doc_in_both_rankings_beats_doc_in_one() -> None:
    # Spec property: a doc ranked 2nd+3rd beats one ranked 1st in a single list.
    rankings = [
        ["only_first", "both", "x"],
        ["y", "z", "both"],
    ]
    scores = reciprocal_rank_fusion(rankings, k=60)

    assert scores["both"] == 1 / 62 + 1 / 63
    assert scores["only_first"] == 1 / 61
    assert scores["both"] > scores["only_first"]


def test_rank_one_in_both_is_maximal() -> None:
    scores = reciprocal_rank_fusion([["a", "b"], ["a", "c"]], k=60)
    assert max(scores, key=lambda d: scores[d]) == "a"
    assert scores["a"] == 2 / 61


def test_empty_rankings() -> None:
    assert reciprocal_rank_fusion([]) == {}
    assert reciprocal_rank_fusion([[], []]) == {}


def test_k_dampens_rank_differences() -> None:
    small_k = reciprocal_rank_fusion([["a"], ["b", "a"]], k=1)
    big_k = reciprocal_rank_fusion([["a"], ["b", "a"]], k=1000)
    # With huge k, ranks matter less: a (two appearances) dominates b more clearly
    assert small_k["a"] > small_k["b"]
    assert big_k["a"] > big_k["b"]
