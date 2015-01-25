from datetime import timedelta
from datetime import datetime
from datetime import date

import collections
import json
import time
import re
import os

import lxml.html

from dateutil.parser import parse

from bs4 import BeautifulSoup

import vanilla

from market import options


def ET():
    return datetime.utcnow() - timedelta(hours=4)


def last_monday(now=None):
    now = now or date.today()
    return now - timedelta(days=now.weekday())


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


def cache_eod(path):
    in_session, dt = last_trading_date()
    stamp = dt.strftime('%Y-%m-%d')
    ttl = 30*60 if in_session else None
    return cache(path+'-%s' % stamp, ttl=ttl)


def cache_monthly(path):
    stamp = date.today().strftime('%Y-%m')
    return cache(path+'-%s' % stamp)


def cache_weekly(path):
    stamp = last_monday().strftime('%Y-%m-%d')
    return cache(path+'-%s' % stamp)


def search(body, text):
    return BeautifulSoup(body).body.find(text=re.compile(text))


def extract(el):
    for s in el.strings:
        s = s.strip()
        if s:
            s = s.replace(u'\xa0', u' ')
            if s.startswith('$'):
                s = numeric(s[1:])
            elif s.startswith('($'):
                s = -1*numeric(s[2:].replace(')', ''))
            return s


def label(s):
    return s.lower().replace(' ', '_').replace(':', '')


def numeric(s):
    if s is None:
        return 0
    bak = s
    try:
        s = s.strip().replace(u',', u'')
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
        body = conn.get(
            '/Trader.aspx', params={'id': 'Calendar'}).recv().consume()
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
        body = ch.recv().consume()
        return body

    @staticmethod
    def parse_realtime(body):
        tree = lxml.html.document_fromstring(body)
        data = {
            'quote': tree.xpath('//div[@id="qwidget_lastsale"]')[0].text,
            'change': tree.xpath('//div[@id="qwidget_netchange"]')[0].text,
            'percent': tree.xpath('//div[@id="qwidget_percent"]')[0].text,
            'when': tree.xpath(
                '//div[@id="qwidget_markettimedate"]//span')[0].text,
            'up': 'arrow-green' in
                tree.xpath('//div[@id="qwidget-arrow"]/div')[0].get('class'), }

        data['change'] = round(float(data['change']), 2)
        data['quote'] = round(float(data['quote'][1:]), 2)

        if len(data['when']) < 11:
            data['when'] += ' - market closed'

        return data

    def summary(self, code):
        path = 'nasdaq/summary/%(code)s/%(code)s' % {'code': code.upper()}

        @cache_eod(path)
        def body():
            target = '/symbol/%(code)s' % {'code': code.lower()}
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

        ret['outstanding'] = int(round(ret['market_cap'] / ret['quote']))
        return ret

    def balance_sheet_annual(self, code):
        path = 'nasdaq/balance_sheet/annual/%(code)s/%(code)s' % {
            'code': code.upper()}

        @cache_monthly(path)
        def body():
            target = '/symbol/%(code)s/financials' % {'code': code.lower()}
            return self.get(target, params={'query': 'balance-sheet'})

        rows = BeautifulSoup(body).find(class_='genTable').find_all('tr')

        want = [
            'total_assets',
            'total_liabilities',
            'total_equity', ]

        key_mapper = {}

        ret = {}
        for row in rows:
            cells = [
                extract(x) for x in row.children if x.name in ('td', 'th')]
            if not cells[0]:
                continue

            key, cols = label(cells[0]), [x for x in cells[2:] if x]
            if not ret:
                periods = [parse(x) for x in cols]
                ret = collections.OrderedDict(
                    (x, collections.OrderedDict()) for x in periods)
            else:
                if key in want:
                    for i, value in enumerate(cols):
                        ret[periods[i]][key_mapper.get(key, key)] = \
                            value * 1000

        return ret

    def income_statement_annual(self, code):
        path = 'nasdaq/income_statement/annual/%(code)s/%(code)s' % {
            'code': code.upper()}

        @cache_monthly(path)
        def body():
            target = '/symbol/%(code)s/financials' % {'code': code.lower()}
            return self.get(target, params={'query': 'income-statement'})

        rows = BeautifulSoup(body).find(class_='genTable').find_all('tr')

        want = [
            'total_revenue',
            'cost_of_revenue',
            'gross_profit',
            'operating_income',
            'earnings_before_interest_and_tax',
            'earnings_before_tax',
            'net_income',
            'net_income_applicable_to_common_shareholders', ]

        key_mapper = {
            'total_revenue': 'sales',
            'net_income_applicable_to_common_shareholders': 'earnings', }

        ret = {}
        for row in rows:
            cells = [
                extract(x) for x in row.children if x.name in ('td', 'th')]
            if not cells[0]:
                continue

            key, cols = label(cells[0]), [x for x in cells[2:] if x]
            if not ret:
                periods = [parse(x) for x in cols]
                ret = collections.OrderedDict(
                    (x, collections.OrderedDict()) for x in periods)
            else:
                if key in want:
                    for i, value in enumerate(cols):
                        ret[periods[i]][key_mapper.get(key, key)] = \
                            value * 1000

        return ret

    def income_statement_quarterly(self, code):
        path = 'nasdaq/income_statement/quarterly/%(code)s/%(code)s' % {
            'code': code.upper()}

        @cache_weekly(path)
        def body():
            target = '/symbol/%(code)s/financials' % {'code': code.lower()}
            return self.get(target,
                params={'query': 'income-statement', 'data': 'quarterly'})

        rows = BeautifulSoup(body).find(class_='genTable').find_all('tr')

        want = [
            'total_revenue',
            'cost_of_revenue',
            'gross_profit',
            'operating_income',
            'earnings_before_interest_and_tax',
            'earnings_before_tax',
            'net_income',
            'net_income_applicable_to_common_shareholders', ]

        key_mapper = {
            'total_revenue': 'sales',
            'net_income_applicable_to_common_shareholders': 'earnings', }

        ret = {}
        for row in rows:
            cells = [
                extract(x) for x in row.children if x.name in ('td', 'th')]
            if not cells[0]:
                continue

            key, cols = label(cells[0]), [x for x in cells[2:] if x]

            if key == 'quarter_ending':
                periods = [parse(x) for x in cols]
                ret = collections.OrderedDict(
                    (x, collections.OrderedDict()) for x in periods)
            else:
                if key in want:
                    for i, value in enumerate(cols):
                        ret[periods[i]][key_mapper.get(key, key)] = \
                            value * 1000

        return ret


class Google(object):
    HOST = "http://www.google.com/"
    PATH = "/finance/option_chain"

    def option_chain(self, code):
        if code.upper() in options._data:
            return list(options.Pool(code))[0]

        path = 'google/option_chain/%(code)s/%(code)s' % {'code': code.upper()}

        @cache_eod(path)
        def body():
            params = {
                'type': 'All',
                'output': 'json',
                'q': code, }

            def expiry_to_str(e):
                return '%04d-%02d-%02d' % (e['y'], e['m'], e['d'])

            h = vanilla.Hub()
            conn = h.http.connect(self.HOST)

            ret = {}

            body = conn.get(self.PATH, params=params).recv().consume()
            body = re.sub(r'(\w+):', r'"\1":', body)
            data = json.loads(body)

            expiry = expiry_to_str(data['expiry'])

            expirations = set(
                expiry_to_str(e) for e in data['expirations'])
            expirations.remove(expiry)

            ret[expiry] = (data['calls'], data['puts'])

            while expirations:
                expiry = expirations.pop()
                y, m, d = expiry.split('-')

                params['expy'], params['expm'], params['expd'] = [
                    int(x) for x in expiry.split('-')]

                body = conn.get(self.PATH, params=params).recv().consume()
                body = re.sub(r'(\w+):', r'"\1":', body)
                data = json.loads(body)

                assert expiry_to_str(data['expiry']) == expiry, \
                    '%s != %s' % (data['expiry'], expiry)

                ret[expiry] = (data['calls'], data['puts'])

            return json.dumps(ret)

        in_session, quote_date = last_trading_date()
        data = json.loads(body)

        base = options._data.setdefault(code.upper(), {})
        base = base.setdefault(quote_date, collections.OrderedDict())

        for expiry in data:
            store = base.setdefault(
                expiry, {
                    'C': collections.OrderedDict(),
                    'P': collections.OrderedDict(), })

            calls, puts = data[expiry]
            for typ, contracts in [('C', calls), ('P', puts)]:
                for contract in contracts:
                    store[typ][float(contract['strike'])] = \
                        options.Contract(
                            *[0 if contract[x] == '-' else float(contract[x])
                                for x in ['b', 'a', 'p', 'vol', 'oi']])

        return options.Pool(code)[quote_date]


class YQL(object):
    HOST = "http://query.yahooapis.com/"
    PATH = "/v1/public/yql"
    DATATABLES_URL = 'store://datatables.org/alltableswithkeys'

    def option_chain(self, code):
        if code.upper() in options._data:
            return list(options.Pool(code))[0]

        path = 'yahoo/option_chain/%(code)s/%(code)s' % {'code': code.upper()}

        @cache_eod(path)
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

            body = conn.get(self.PATH, params=params).recv().consume()
            data = json.loads(body)
            assert data['query']['results']
            return body

        in_session, quote_date = last_trading_date()
        data = json.loads(body)

        base = options._data.setdefault(code.upper(), {})
        base = base.setdefault(quote_date, collections.OrderedDict())

        for chain in data['query']['results']['optionsChain']:
            for strike in chain['option']:
                expiry = strike['symbol'][len(code):len(code)+6]
                expiry = '20%s-%s-%s' % (expiry[:2], expiry[2:4], expiry[4:])
                store = base.setdefault(
                    expiry, {
                        'C': collections.OrderedDict(),
                        'P': collections.OrderedDict(), })
                store[strike['type']][strike['strikePrice']] = \
                    options.Contract(
                        *[float(strike[x]) for x in
                            ['bid', 'ask', 'lastPrice', 'vol', 'openInt']])

        return options.Pool(code)[quote_date]


class Estimize(object):
    HOST = 'http://www.estimize.com'

    def estimate(self, code):
        path = 'estimize/earnings/%(code)s/%(code)s' % {'code': code.upper()}

        @cache_weekly(path)
        def body():
            h = vanilla.Hub()
            conn = h.http.connect(self.HOST)
            ch = conn.get('/%s' % code.lower())
            body = ch.recv().consume()
            return body

        ret = collections.OrderedDict()

        if BeautifulSoup(body).find('h1').text == 'Page Not Found':
            return ret

        dt = search(body, 'to report').parent.find('span').text.split()[0]
        dt = parse(dt)
        ret.to_report = dt

        script = search(body, 'Estimize.ReleaseCollection')
        data = script.split('Estimize.ReleaseCollection(')[1].split(')')[0]
        data = json.loads(data)

        class Quarter(object):
            pass

        Estimate = collections.namedtuple(
            'Estimate', ['actual', 'wallst', 'estimize'])

        for item in data:
            q = Quarter()
            q.earnings = Estimate(
                item['eps'],
                item['wallstreet_eps_mean'],
                item['estimize_eps_mean'])
            q.revenue = Estimate(
                item['revenue'],
                item['wallstreet_revenue_mean'],
                item['estimize_revenue_mean'])
            ret[item['name']] = q
        return ret
