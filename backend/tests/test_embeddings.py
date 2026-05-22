from app.services import embeddings


def test_embed_empty_list_returns_empty():
    assert embeddings.embed([]) == []


def test_embed_maps_model_output_to_float_lists(monkeypatch):
    class FakeModel:
        def embed(self, texts):
            return [[0.1, 0.2, 0.3] for _ in texts]

    monkeypatch.setattr(embeddings, "_get_model", lambda: FakeModel())
    out = embeddings.embed(["alpha", "beta"])
    assert out == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert all(isinstance(v, float) for v in out[0])


def test_embed_returns_empty_on_model_failure(monkeypatch):
    def boom():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(embeddings, "_get_model", boom)
    assert embeddings.embed(["alpha"]) == []
