from policyiq.config import Settings, Thresholds, _load_thresholds


def test_thresholds_have_sane_defaults():
    thresholds = Thresholds()
    assert 0.0 < thresholds.confidence_floor < 1.0
    assert 0.0 < thresholds.min_relevance_score < 1.0
    assert thresholds.max_retrieval_attempts >= 1
    assert thresholds.chunk_overlap_chars < thresholds.chunk_size_chars


def test_thresholds_load_from_project_yaml():
    thresholds = _load_thresholds()
    assert thresholds.confidence_floor == 0.6
    assert thresholds.top_k == 4


def test_settings_do_not_require_openai_key_to_construct():
    settings = Settings(_env_file=None, openai_api_key=None)
    assert settings.openai_api_key is None
