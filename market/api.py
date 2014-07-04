import time
import re
import os

from bs4 import BeautifulSoup

import vanilla


def cache(f):
    def wrap(*a, **kw):
        name = '.'.join([f.__name__] + list(a[1:]))
        path = os.path.expanduser('~/.market/cache/%s' % name)

        # TODO: enforce cache if it's out of hours
        return open(path).read()

        try:
            last = os.path.getmtime(path)
            if time.time() - last < 30*60:
                return open(path).read()
        except OSError:
            pass
        data = f(*a, **kw)
        open(path, 'w').write(data)
        return data
    return wrap


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

    @cache
    def _summary_dl(self, code):
        target = '/symbol/%(code)s' % {'code': code}
        return self.get(target)

    def _summary_parse(self, body):
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

    def summary(self, code):
        body = self._summary_dl(code)
        return self._summary_parse(body)
