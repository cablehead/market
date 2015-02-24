import os

from datetime import datetime
from datetime import date

from market import api


class TestNasdaq(object):
    """
    def test_summary(self):
        nasdaq = api.Nasdaq()
        assert 'market_cap' in nasdaq.summary('chl')

    def test_income_statement_annual(self):
        nasdaq = api.Nasdaq()
        nasdaq.income_statement_annual('chl')

    def test_income_statement_quarterly(self):
        nasdaq = api.Nasdaq()
        got = nasdaq.income_statement_quarterly('mu')


    def test_balance_sheet_annual(self):
        nasdaq = api.Nasdaq()
        nasdaq.balance_sheet_annual('chl')
    """

    def body(self, name):
        return open(os.path.join(
            os.path.dirname(__file__), 'data', name)).read()

    def test_parse_realtime(self):
        body = self.body('nasdaq.realtime-pre.html')
        assert api.Nasdaq.parse_realtime(body) == {
            'quote': 111.5,
            'when': '12/18/2014 8:08:42 AM',
            'percent': '1.91%',
            'up': True,
            'change': 2.09, }

        body = self.body('nasdaq.realtime-interday.html')
        assert api.Nasdaq.parse_realtime(body) == {
            'quote': 111.78,
            'when': '12/18/2014 2:44:23 PM',
            'percent': '2.17%',
            'up': True,
            'change': 2.37, }

        body = self.body('nasdaq.realtime-closed.html')
        assert api.Nasdaq.parse_realtime(body) == {
            'quote': 112.65,
            'when': '12/18/2014 - market closed',
            'percent': '2.96%',
            'up': True,
            'change': 3.24, }


def test_YQL():
    """
    yql = api.YQL()
    yql.option_chain('fb')
    yql.option_chain('fb')
    """


def test_Estimize():
    """
    e = api.Estimize()
    e.estimate('outr').to_report
    """


def test_calendar():
    assert date(2014, 7, 4) in api.calendar()['closed']
    assert date(2015, 5, 25) in api.calendar()['closed']


def test_last_monday():
    now = mon = date(2014, 7, 7)  # MON
    assert api.last_monday(now) == mon
    now = date(2014, 7, 8)  # TUE
    assert api.last_monday(now) == mon
    now = date(2014, 7, 13)  # SUN
    assert api.last_monday(now) == mon


def test_last_trading_date():
    now = datetime(2014, 6, 23, 9, 29)  # MON
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 20, 16, 0))
    now = datetime(2014, 6, 23, 9, 30)
    assert api.last_trading_date(now) == (True, datetime(2014, 6, 23, 16, 0))
    now = datetime(2014, 6, 23, 16, 01)
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 23, 16, 0))

    now = datetime(2014, 6, 25, 9, 29, 25, 386164)  # WED
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 24, 16, 0))
    now = datetime(2014, 6, 25, 9, 30)
    assert api.last_trading_date(now) == (True, datetime(2014, 6, 25, 16, 0))
    now = datetime(2014, 6, 25, 16, 01)
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 25, 16, 0))

    now = datetime(2014, 6, 28, 9, 29)  # SAT
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 27, 16, 0))
    now = datetime(2014, 6, 28, 9, 30)
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 27, 16, 0))
    now = datetime(2014, 6, 28, 16, 01)
    assert api.last_trading_date(now) == (False, datetime(2014, 6, 27, 16, 0))

    now = datetime(2014, 7, 03, 9, 29, 25, 386164)  # THU, the 3rd
    assert api.last_trading_date(now) == (False, datetime(2014, 7, 02, 16, 0))
    now = datetime(2014, 7, 03, 9, 30)
    assert api.last_trading_date(now) == (True, datetime(2014, 7, 03, 13, 0))
    now = datetime(2014, 7, 03, 13, 01)  # Market closes early
    assert api.last_trading_date(now) == (False, datetime(2014, 7, 03, 13, 0))

    now = datetime(2014, 7, 04, 9, 29, 25, 386164)  # FRI, the 4th
    assert api.last_trading_date(now) == (False, datetime(2014, 7, 03, 13, 0))
    now = datetime(2014, 7, 04, 9, 30)
    assert api.last_trading_date(now) == (False, datetime(2014, 7, 03, 13, 0))
    now = datetime(2014, 7, 04, 16, 01)
    assert api.last_trading_date(now) == (False, datetime(2014, 7, 03, 13, 0))
