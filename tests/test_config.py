"""設定読み込みのテスト."""

import pytest

from zazoo_ads.config import ApiCredentials, RulesConfig


def test_rules_from_dict_defaults():
    cfg = RulesConfig.from_dict({})
    assert cfg.bid.target_acos == 0.30
    assert cfg.budget.enabled is True


def test_rules_from_dict_override():
    cfg = RulesConfig.from_dict({"bid": {"target_acos": 0.25}})
    assert cfg.bid.target_acos == 0.25
    # 他はデフォルト
    assert cfg.bid.min_clicks == 10


def test_rules_unknown_key_raises():
    with pytest.raises(ValueError):
        RulesConfig.from_dict({"bid": {"nope": 1}})


def test_credentials_endpoint_fe():
    cred = ApiCredentials(
        client_id="a", client_secret="b", refresh_token="c",
        profile_id="d", region="FE",
    )
    assert cred.endpoint.endswith("-fe.amazon.com")


def test_credentials_lwa_urls_fe():
    cred = ApiCredentials(
        client_id="a", client_secret="b", refresh_token="c",
        profile_id="d", region="FE",
    )
    # 日本(FE)は co.jp / apac ドメインでなければならない
    assert cred.lwa_token_url == "https://api.amazon.co.jp/auth/o2/token"
    assert cred.lwa_auth_url == "https://apac.account.amazon.com/ap/oa"


def test_credentials_lwa_urls_na():
    cred = ApiCredentials(
        client_id="a", client_secret="b", refresh_token="c",
        profile_id="d", region="NA",
    )
    assert cred.lwa_token_url == "https://api.amazon.com/auth/o2/token"


def test_credentials_unknown_region():
    cred = ApiCredentials(
        client_id="a", client_secret="b", refresh_token="c",
        profile_id="d", region="ZZ",
    )
    with pytest.raises(ValueError):
        _ = cred.endpoint


def test_credentials_from_env_missing(monkeypatch):
    for k in ("ADS_CLIENT_ID", "ADS_CLIENT_SECRET", "ADS_REFRESH_TOKEN", "ADS_PROFILE_ID"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError):
        ApiCredentials.from_env()


def test_credentials_from_env_ok(monkeypatch):
    monkeypatch.setenv("ADS_CLIENT_ID", "a")
    monkeypatch.setenv("ADS_CLIENT_SECRET", "b")
    monkeypatch.setenv("ADS_REFRESH_TOKEN", "c")
    monkeypatch.setenv("ADS_PROFILE_ID", "d")
    monkeypatch.setenv("ADS_REGION", "NA")
    cred = ApiCredentials.from_env()
    assert cred.region == "NA"
    assert cred.profile_id == "d"
