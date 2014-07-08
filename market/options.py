import collections

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

    def __contains__(self, key):
        return key in self.node

    def __getitem__(self, key):
        if not key in self.node:
            self.node[key] = {}
        return self.__next__(list(self.path)+[key])

    def __iter__(self):
        keys = self.node.keys()
        keys.sort()
        for key in keys:
            yield self.__next__(list(self.path)+[key])

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
        dt, e, t, s = self.path
        t = t == "C" and "P" or "C"
        typ = Typ(self.data, [dt, e, t])
        if s in typ:
            return typ[s]

    def __getattr__(self, name):
        return getattr(self.node, name)

    def __summary__(self):
        return "last: %s" % self.node.last


class Typ(Node):
    __next__ = Strike

    def __setitem__(self, key, value):
        self.node[key] = value


class Expiry(Node):
    __next__ = Typ

    @property
    def c(self):
        return self["C"]

    @property
    def p(self):
        return self["P"]


class Quote(Node):
    __next__ = Expiry


class Pool(Node):
    __next__ = Quote

    def __init__(self, code):
        return super(Pool, self).__init__(path=[code.upper()])
