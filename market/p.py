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
        self.color = color or (lambda x: None)

    def format(self, value):
        if not self.fmt:
            return value
        return format(value, self.fmt)


terminal = colorconsole.terminal.get_terminal()


class Split(object):
    def __init__(self):
        self.lines = [[]]

    def write(self, s, width=None, color=None):
        self.lines[-1].append((s, width, color))

    def nl(self):
        self.lines.append([])


class D(object):
    def __init__(self):
        self.terminal = colorconsole.terminal.get_terminal()
        self.num_cols, self.num_rows = getTerminalSize()
        # self.terminal.move_right(self.num_cols/2)

    def write(self, s, width=None, color=None):
        if color:
            self.terminal.xterm256_set_fg_color(color)
            self.terminal.putch(s)
            self.terminal.reset()
        else:
            self.terminal.putch(s)

        if width:
            self.terminal.move_right(width - len(s))

    def nl(self):
        self.terminal.putch('\n')
        # self.terminal.move_right(self.num_cols/2)

    def render(self, split):
        for line in split.lines[:-1]:
            for a in line:
                self.write(*a)
            self.nl()


# http://stackoverflow.com/a/566752/729767
def getTerminalSize():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])
