from market import api


def test_nasdaq():
    nasdaq = api.Nasdaq()
    assert 'market_cap' in nasdaq.summary('chl')
