import colorconsole.terminal


colors = [116, 173, 83, 63, 36, 126, 106, 226, 201, 51, 46, 196, 20, 231]


class ColorDistinct(object):
    def __init__(self):
        self.assigned = {}

    def get(self, name):
        if name not in self.assigned:
            self.assigned[name] = colors[len(self.assigned)]
        return self.assigned[name]


class Column(object):
    def __init__(self, name, fmt=None, color=None):
        self.name = name
        self.fmt = fmt
        self.color = color

    def format(self, value):
        if not self.fmt:
            return value
        return format(value, self.fmt)


terminal = colorconsole.terminal.get_terminal()
