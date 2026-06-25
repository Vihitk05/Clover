from config.settings import config


def test_config_smoke():
    assert config.validate(report=False) is True
    assert config.DATABASE_URL.startswith("postgresql://")
    assert isinstance(config.GENERATION_THRESHOLD, int)
