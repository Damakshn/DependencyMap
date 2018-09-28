class Mark(object):

    def __init__(self, position, line):
        self.pos = position
        self.line = line

    def __repr__(self):
        return "{}".format(str(self.line))
