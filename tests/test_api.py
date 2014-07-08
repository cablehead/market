from datetime import datetime
from datetime import date

from market import api


class TestNasdaq(object):
    def test_summary(self):
        nasdaq = api.Nasdaq()
        assert 'market_cap' in nasdaq.summary('chl')

    def test_income_statement_annual(self):
        nasdaq = api.Nasdaq()
        nasdaq.income_statement_annual('chl')

    def test_balance_sheet_annual(self):
        nasdaq = api.Nasdaq()
        nasdaq.balance_sheet_annual('chl')


def test_YQL():
    yql = api.YQL()
    yql.option_chain('fb')
    yql.option_chain('fb')


def test_calendar():
    assert date(2014, 7, 4) in api.calendar()['closed']


def test_last_trading_date():
    now = datetime(2014, 6, 23, 9, 29)  # MON
    assert api.last_trading_date(now) == (False, date(2014, 6, 20))
    now = datetime(2014, 6, 23, 9, 30)
    assert api.last_trading_date(now) == (True, date(2014, 6, 23))
    now = datetime(2014, 6, 23, 16, 01)
    assert api.last_trading_date(now) == (False, date(2014, 6, 23))

    now = datetime(2014, 6, 25, 9, 29, 25, 386164)  # WED
    assert api.last_trading_date(now) == (False, date(2014, 6, 24))
    now = datetime(2014, 6, 25, 9, 30)
    assert api.last_trading_date(now) == (True, date(2014, 6, 25))
    now = datetime(2014, 6, 25, 16, 01)
    assert api.last_trading_date(now) == (False, date(2014, 6, 25))

    now = datetime(2014, 6, 28, 9, 29)  # SAT
    assert api.last_trading_date(now) == (False, date(2014, 6, 27))
    now = datetime(2014, 6, 28, 9, 30)
    assert api.last_trading_date(now) == (False, date(2014, 6, 27))
    now = datetime(2014, 6, 28, 16, 01)
    assert api.last_trading_date(now) == (False, date(2014, 6, 27))

    now = datetime(2014, 7, 03, 9, 29, 25, 386164)  # THU, the 3rd
    assert api.last_trading_date(now) == (False, date(2014, 7, 02))
    now = datetime(2014, 7, 03, 9, 30)
    assert api.last_trading_date(now) == (True, date(2014, 7, 03))
    now = datetime(2014, 7, 03, 13, 01)  # Market closes early
    assert api.last_trading_date(now) == (False, date(2014, 7, 03))

    now = datetime(2014, 7, 04, 9, 29, 25, 386164)  # FRI, the 4th
    assert api.last_trading_date(now) == (False, date(2014, 7, 03))
    now = datetime(2014, 7, 04, 9, 30)
    assert api.last_trading_date(now) == (False, date(2014, 7, 03))
    now = datetime(2014, 7, 04, 16, 01)
    assert api.last_trading_date(now) == (False, date(2014, 7, 03))
