from app.analysis import news_clustering as nc


def test_cosine_similarity():
    assert nc.cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert nc.cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert nc.cosine_similarity([], [1.0, 0.0]) == 0.0
    assert nc.cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cluster_articles_groups_similar_vectors():
    vectors = [[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]]
    groups = nc.cluster_articles(vectors, threshold=0.6)
    # two near-identical vectors cluster; the orthogonal one stands alone
    assert sorted(len(g) for g in groups) == [1, 2]


def test_cluster_articles_all_distinct():
    groups = nc.cluster_articles([[1.0, 0.0], [0.0, 1.0]], threshold=0.6)
    assert sorted(len(g) for g in groups) == [1, 1]


def test_cluster_by_title_groups_normalized_titles():
    groups = nc.cluster_by_title(["Big News!", "big news", "Other story"])
    assert sorted(len(g) for g in groups) == [1, 2]


def test_pick_representative_is_earliest_published():
    pubs = ["2026-05-22T05:00:00+00:00",
            "2026-05-22T01:00:00+00:00",
            "2026-05-22T09:00:00+00:00"]
    assert nc.pick_representative(pubs) == 1
    assert nc.pick_representative([]) == 0
