from datetime import datetime

import os

from dateutil.parser import parse

from market import api


class Position(object):
    def __init__(self, code, expiry, typ_, strike, amount, paid, when):
        self.code = code
        self.expiry = expiry
        self.typ_ = typ_
        self.strike = strike
        self.when = when
        self.amount = int(amount)
        self.paid = float(paid)

    @property
    def quote(self):
        quote = api.YQL().option_chain(self.code)
        return quote[self.expiry][self.typ_][self.strike]

    @property
    def basis(self):
        return self.amount * self.paid * 100

    @property
    def current(self):
        return self.amount * self.quote.last * 100

    @property
    def togo(self):
        return (parse(self.expiry) - datetime.now()).days

    @property
    def held(self):
        return (datetime.now() - parse(self.when)).days


class Spread(object):
    def __init__(self):
        self.positions = []

    @property
    def code(self):
        return self.positions[0].code

    @property
    def expiry(self):
        return self.positions[0].expiry

    @property
    def basis(self):
        return sum(x.basis for x in self.positions)

    @property
    def current(self):
        return sum(x.current for x in self.positions)

    @property
    def delta(self):
        return self.current - self.basis

    @property
    def perc(self):
        return '%2d%%' % abs(int(
            ((self.current - self.basis) / self.basis) * 100))

    @property
    def togo(self):
        return self.positions[0].togo

    @property
    def held(self):
        return self.positions[0].held

    def __repr__(self):
        s = ' '.join('%s: %s' % (x, getattr(self, x)) for x in [
            'expiry',
            'basis',
            'current',
            'delta',
            'perc',
            'togo',
            'held', ])
        return '<Spread %-4s %s>' % (self.code, s)


class Portfolio(object):
    def __init__(self):
        self.spreads = []

        path = os.path.expanduser('~/.market/portfolio')
        fh = open(path)

        try:
            while True:
                line = fh.next()
                if line.strip() == 'SPREAD':
                    spread = Spread()
                    self.spreads.append(spread)
                    while True:
                        line = fh.next()
                        if not line.startswith(' '):
                            break
                        spread.positions.append(
                            Position(*line.strip().split()))
        except StopIteration:
            pass
