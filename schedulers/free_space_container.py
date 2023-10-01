from .free_space import FreeSpace

INFINITY = float('inf')

class FreeSpaceContainer(object):
    """
    Developers, NEVER FORGET:
    - operations on the list can be done will iterating on it with the generator()
    - when on BF mode, 2 consecutives items can have the same first_res or last_res.
    """

    def __init__(self, total_processors):
        self.firstItem = FreeSpace(
            0, total_processors - 1, INFINITY, None, None)
        self.free_processors = total_processors

    def generator(self):
        curit = self.firstItem
        while curit is not None:
            yield curit
            curit = curit.nextt

    def remove(self, item):
        prev = item.prev
        nextt = item.nextt
        if item == self.firstItem:
            self.firstItem = nextt
        else:
            assert prev is not None, "The self.firstItem () should be set to" \
                ", but its not!".format(self.firstItem, item)
            prev.nextt = nextt
        if nextt is not None:
            nextt.prev = prev
        # if someone hold a direct refecence to item, it can knwo if this item
        # have been removed from the list
        item.removed = True

    def _assignJobBeginning(self, l, job):
        alloc = (l.first_res, l.first_res + job.requested_resources - 1)
        l.first_res = l.first_res + job.requested_resources
        l.res = l.last_res - l.first_res + 1
        assert l.res >= 0
        if l.res == 0:
            self.remove(l)
        return alloc

    def _assignJobEnding(self, l, job):
        alloc = (l.last_res - job.requested_resources + 1, l.last_res)
        l.last_res = l.last_res - job.requested_resources
        l.res = l.last_res - l.first_res + 1
        assert l.res >= 0
        if l.res == 0:
            self.remove(l)
        return alloc

    def assignJob(self, l, job, current_time):
        assert job.requested_resources <= l.res
        # TODO:here we can alloc close to job that will end as the same time as
        # the current job
        if l.allocSmallestResFirst:
            alloc = self._assignJobBeginning(l, job)
            # remove the resources of the linked FreeSpace (see allocFutureJob)
            if hasattr(l, "linkedTo"):
                if l.linkedTo.first_res <= alloc[1]:
                    l.linkedTo.first_res = alloc[1] + 1

        else:
            alloc = self._assignJobEnding(l, job)
            # remove the resources of the linked FreeSpace (see allocFutureJob)
            if hasattr(l, "linkedTo"):
                if l.linkedTo.last_res >= alloc[0]:
                    l.linkedTo.last_res = alloc[0] - 1
        job.alloc = alloc

        if hasattr(l, "linkedTo") and not hasattr(l.linkedTo, "removed"):
            l.linkedTo.res = l.linkedTo.last_res - l.linkedTo.first_res + 1
            if l.linkedTo.res <= 0:
                self.remove(l.linkedTo)

        self.free_processors -= job.requested_resources

        return alloc

    def _findSurroundingFreeSpaces(self, job):
        prev_fspc = None
        for fspc in self.generator():
            if fspc.first_res > job.alloc[0]:
                return (prev_fspc, fspc)
            prev_fspc = fspc
        # prev_fspc = last fspc
        return (prev_fspc, None)

    def unassignJob(self, job):
        self.free_processors += job.requested_resources

        (l1, l2) = self._findSurroundingFreeSpaces(job)

        # merge with l1?
        mergel1 = ((l1 is not None) and (l1.last_res + 1 == job.alloc[0]))
        mergel2 = ((l2 is not None) and (l2.first_res - 1 == job.alloc[-1]))
        if mergel1 and mergel2:
            # merge l2 into l1
            l1.nextt = l2.nextt
            if l1.nextt is not None:
                l1.nextt.prev = l1
            l1.last_res = l2.last_res
            l1.res = l1.last_res - l1.first_res + 1
            assert l1.first_res <= l1.last_res, str(l1) + " // " + str(job)
            return l1
        elif mergel1:
            # increase l1 size
            l1.last_res = l1.last_res + job.requested_resources
            l1.res = l1.last_res - l1.first_res + 1
            # we will alloc jobs close to where the last job were scheduled
            l1.allocSmallestResFirst = False
            assert l1.first_res <= l1.last_res, str(l1) + " // " + str(job)
            return l1
        elif mergel2:
            # increase l2 size
            l2.first_res = l2.first_res - job.requested_resources
            l2.res = l2.last_res - l2.first_res + 1
            # we will alloc jobs close to where the last job were scheduled
            l2.allocSmallestResFirst = True
            assert l2.first_res <= l2.last_res, str(l2) + " // " + str(job)
            return l2
        else:
            # create a new freespace
            lnew = FreeSpace(job.alloc[0], job.alloc[-1], INFINITY, l1, l2)

            if l1 is None:
                self.firstItem = lnew
            else:
                l1.nextt = lnew
            if l2 is not None:
                l2.prev = lnew

            return lnew
        assert False

    def printme(self):
        print("-------------------")
        for l in self.generator():
            print(str(l))
        print("-------------------")

    def insertNewFreeSpaceAfter(self, first_res, last_res, len, l):
        newfs = FreeSpace(first_res, last_res, len, l, l.nextt)

        if l.nextt is not None:
            l.nextt.prev = newfs

        l.nextt = newfs

        return newfs

    def copy(self):
        n = FreeSpaceContainer(42)
        n.free_processors = self.free_processors

        if self.firstItem is None:
            n.firstItem = None
        else:
            curit = self.firstItem.copy()
            fi = curit
            while not(curit.nextt is None):
                curit.nextt = curit.nextt.copy()
                curit.nextt.prev = curit
                # this assert forbid to copy a FreeSpaceContainer that has done
                # the backfill reservation
                assert curit.last_res < curit.nextt.first_res, str(
                    curit) + " // " + str(curit.nextt)
                curit = curit.nextt
            n.firstItem = fi
        return n