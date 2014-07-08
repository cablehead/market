import os


class Position(object):
    def __init__(self, code, expiry, typ_, strike, amount, paid):
        self.code = code
        self.expiry = expiry
        self.typ_ = typ_
        self.strike = strike
        self.amount = int(amount)
        self.paid = float(paid)


class Spread(object):
    def __init__(self):
        self.positions = []


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
