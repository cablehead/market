from datetime import timedelta
from datetime import datetime

import json
import time
import re
import os

from dateutil.parser import parse

from bs4 import BeautifulSoup

import vanilla


def ET():
    return datetime.utcnow() - timedelta(hours=4)


def last_trading_date(now=None):
    now = now or ET()
    now = now.replace(second=0, microsecond=0)

    cal = calendar()

    def opened(when):
        return when.weekday() < 5 and when not in cal['closed']

    def last_opened(when):
        while True:
            when = when - timedelta(days=1)
            if opened(when):
                return when

    if not opened(now.date()):
        return False, last_opened(now.date())

    opening = now.replace(hour=9, minute=30)
    if now < opening:
        return False, last_opened(now.date())

    if now.date() in cal['1pm']:
        closing = now.replace(hour=13, minute=0)
    else:
        closing = now.replace(hour=16, minute=0)

    return bool(now < closing), now.date()


def cache(path, ttl=None):
    def decorate(f):
        full = os.path.expanduser('~/.market/%s' % path)

        if os.path.exists(full):
            if ttl is None or time.time() - os.path.getmtime(full) < ttl:
                return open(full).read()

        try:
            os.makedirs(os.path.dirname(full))
        except:
            pass

        ret = f()
        open(full, 'w').write(ret)
        return ret

    return decorate


def cache_eod(path, dt):
    in_session, dt = last_trading_date(dt)
    stamp = dt.strftime('%Y-%m-%d')
    ttl = 30*60 if in_session else None
    return cache(path+'-%s' % stamp, ttl=ttl)


def search(body, text):
    return BeautifulSoup(body).body.find(text=re.compile(text))


def extract(el):
    for s in el.strings:
        s = s.strip()
        if s:
            s = s.replace(u'\xa0', u' ')
            if s.startswith('$'):
                s = numeric(s[2:])
            return s


def numeric(s):
    if s is None:
        return 0
    bak = s
    try:
        s = s.replace(u',', u'')
        if '.' in s:
            s = float(s)
        else:
            s = int(s)
    except:
        s = bak
    return s


def calendar():
    @cache('nasdaqtrader/calendar')
    def body():
        h = vanilla.Hub()
        conn = h.http.connect('http://www.nasdaqtrader.com/')
        ch = conn.get('/Trader.aspx', params={'id': 'Calendar'})
        ch.recv()  # status
        ch.recv()  # headers
        body = ch.recv()
        return body

    @cache('nasdaqtrader/calendar.json')
    def rows():
        locate = BeautifulSoup(body).find(class_='dataTable').find_all('tr')
        rows = []
        for row in locate[1:]:
            rows.append([extract(x) for x in row.find_all('td')])
        return json.dumps(rows)

    ret = {'closed': set(), '1pm': set()}
    for dt, name, state in json.loads(rows):
        dt = parse(dt).date()
        if state == 'Closed':
            ret['closed'].add(dt)
        else:
            assert state == '1:00 p.m.'
            ret['1pm'].add(dt)
    return ret


class Nasdaq(object):
    HOST = 'http://www.nasdaq.com/'

    USER_AGENT = 'Mozilla/5.0 (Windows NT 6.3; ' \
                 'Win64; x64) AppleWebKit/537.36 ' \
                 '(KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'

    def get(self, target, params=None):
        h = vanilla.Hub()
        conn = h.http.connect(self.HOST)
        params = params or {}
        ch = conn.get(
            target, headers={'User-Agent': self.USER_AGENT}, params=params)
        ch.recv()  # status
        ch.recv()  # headers
        body = ''.join(list(ch))
        return body

    def summary(self, code):
        path = 'nasdaq/summary/%(code)s/%(code)s' % {'code': code.upper()}

        @cache_eod(path, datetime.now())
        def body():
            target = '/symbol/%(code)s' % {'code': code}
            return self.get(target)

        ret = {}
        mapper = {
            'current_yield': lambda s: float(s[:-1].strip()),
        }

        locate = BeautifulSoup(body).find(id='qwidget_lastsale')
        ret['quote'] = float(locate.text[1:])

        locate = search(body, 'Industry:')
        ret['industry'] = locate.parent.parent.find('a').text

        locate = search(body, 'Market cap')
        for row in locate.find_parent('table').find_all('tr'):
            key, value = [extract(td) for td in row.find_all('td')]
            key = key.lower()
            for ch in ':()/':
                key = key.replace(ch, '')
            key = key.replace(' ', '_')
            value = mapper.get(key, lambda s: s)(value)
            ret[key] = value
        return ret


class YQL(object):
    HOST = "http://query.yahooapis.com/"
    PATH = "/v1/public/yql"
    DATATABLES_URL = 'store://datatables.org/alltableswithkeys'

    def option_chain(self, code):
        path = 'yahoo/option_chain/%(code)s/%(code)s' % {'code': code.upper()}

        @cache_eod(path, datetime.now())
        def body():
            params = {
                'format': 'json',
                'env': self.DATATABLES_URL, }

            query = """
                SELECT *
                FROM yahoo.finance.options
                WHERE
                    symbol="%(code)s" AND
                    expiration in (
                        SELECT contract
                        FROM yahoo.finance.option_contracts
                        WHERE symbol="%(code)s")
            """

            params['q'] = query % {'code': code}

            h = vanilla.Hub()
            conn = h.http.connect(self.HOST)

            ch = conn.get(self.PATH, params=params)
            ch.recv()  # status
            ch.recv()  # headers
            body = ''.join(list(ch))
            return body
        return json.loads(body)
