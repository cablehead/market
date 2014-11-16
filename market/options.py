from datetime import datetime

import collections
import bisect

from dateutil.parser import parse

try:
    import msgpack
except:
    msgpack = False


Contract = collections.namedtuple(
    'Contract', ['bid', 'ask', 'last', 'vol', 'oi'])


# _data["code"]["quote_date"]["expire_date"]["C|P"]["strike"] = contract
_data = {}


"""
def load():
    global _data
    path = "./data/options/SPY/SPY.msgpack"
    _data = msgpack.unpackb(open(path).read())
    return Pool()
"""


"""
these actions should be efficient
contract
    -> different expiry
    -> different contract
    -> different quote date
    -> opposite type
"""


class Node(object):
    def __init__(self, path=None):
        self.path = path or []

    @property
    def node(self):
        ret = _data
        for x in self.path:
            ret = ret[x]
        return ret

    def iterkeys(self):
        return self.node.iterkeys()

    def keys(self):
        return self.node.keys()

    def next(self):
        peers = _data
        for x in self.path[:-1]:
            peers = peers[x]
        keys = peers.keys()
        keys.sort()
        return self.__class__(
            self.path[:-1]+[keys[keys.index(self.path[-1])+1]])

    def __contains__(self, key):
        return key in self.node

    def __getitem__(self, key):
        if key not in self.node:
            self.node[key] = {}
        return self.__child__(list(self.path)+[key])

    def __iter__(self):
        keys = sorted(self.node.iterkeys())
        for key in keys:
            yield self.__child__(list(self.path)+[key])

    def __repr__(self):
        extra = ""
        if hasattr(self, "__summary__"):
            extra = ", %s" % self.__summary__()
        return "<%s: %s%s>" % (
            self.__class__.__name__,
            ", ".join([str(x) for x in self.path]),
            extra)


class Strike(Node):
    @property
    def flip(self):
        dt, expiry, e, t, s = self.path
        t = t == "C" and "P" or "C"
        typ = Typ([dt, expiry, e, t])
        if s in typ:
            return typ[s]

    def __getattr__(self, name):
        return getattr(self.node, name)

    def __summary__(self):
        return "bid: %s ask: %s" % (self.node.bid, self.node.ask)


class Typ(Node):
    __child__ = Strike

    def __setitem__(self, key, value):
        self.node[key] = value

    def at(self, price):
        last = 0
        for key in self.iterkeys():
            if abs(price - key) > abs(price - last):
                return self[last]
            last = key

    def near(self, price, n):
        keys = self.keys()
        index = bisect.bisect(keys, price)
        return [self[key] for key in keys[index-n:index+n]]


class Expiry(Node):
    __child__ = Typ

    @property
    def c(self):
        return self["C"]

    @property
    def p(self):
        return self["P"]

    @property
    def togo(self):
        return (parse(self.path[-1]) - datetime.now()).days

    def __summary__(self):
        return "togo: %s" % self.togo


class Quote(Node):
    __child__ = Expiry


class Pool(Node):
    __child__ = Quote

    def __init__(self, code):
        return super(Pool, self).__init__(path=[code.upper()])
