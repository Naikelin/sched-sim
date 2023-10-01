class FreeSpace(object):

    def __init__(self, first_res, last_res, len, p, n):
        self.first_res = first_res
        self.last_res = last_res
        self.res = last_res - first_res + 1
        self.length = len
        self.prev = p
        self.nextt = n
        self.allocSmallestResFirst = True
        assert first_res <= last_res, str(self)

    def __repr__(self):
        if self.prev is None:
            p = "|"
        else:
            p = "<"
        if self.nextt is None:
            n = "|"
        else:
            n = ">"
        if hasattr(self, "linkedTo"):
            link = "L(" + str(self.linkedTo.first_res) + \
                "-" + str(self.linkedTo.last_res) + ")"
        else:
            link = ""
        if hasattr(self, "removed"):
            delet = "NOTinLIST"
        else:
            delet = ""
        if self.allocSmallestResFirst:
            asrf1 = "*"
            asrf2 = " "
        else:
            asrf1 = " "
            asrf2 = "*"
        return "<<FreeSpace [{}-{}] {} {} \t{} {} {} {}\t>>".format(
            self.first_res, self.last_res, self.length, link,
            asrf1, p, n, asrf2, delet)

    def copy(self):
        n = FreeSpace(self.first_res, self.last_res,
                      self.length, self.prev, self.nextt)
        n.allocSmallestResFirst = self.allocSmallestResFirst
        if hasattr(self, "linkedTo"):
            n.linkedTo = self.linkedTo
        if hasattr(self, "removed"):
            n.removed = self.removed
        return n
