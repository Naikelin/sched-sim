import copy

class SimWithQ:
    def __init__(self, free_space, jobs):
        self.virtual_free_space = copy.deepcopy(free_space)
        self.jobs = jobs

    def simulate(self):
        """Simulate the total completion time for the provided order of jobs."""
        virtual_time = 0
        virtual_running_jobs = []
        total_completion_time = 0

        for job in self.jobs:
            alloc = self.virtual_assign_job(job, virtual_time)
            
            if alloc:
                virtual_running_jobs.append((job, job.requested_time + virtual_time))
                self.update_virtual_free_space(job, alloc)
                
                shortest_time = min(virtual_running_jobs, key=lambda x: x[1])[1]
                virtual_time = shortest_time
                virtual_running_jobs = [j for j in virtual_running_jobs if j[1] > virtual_time]
                total_completion_time += virtual_time
            else:
                virtual_time += 1

        return total_completion_time

    def virtual_assign_job(self, job, virtual_time):
        """Simulated assignment of a job to a free space without affecting the real state."""
        for l in self.virtual_free_space.generator():
            if job.requested_resources <= l.res and (virtual_time + job.requested_time) <= l.length:
                first_res = l.first_res
                last_res = l.first_res + job.requested_resources - 1
                return (first_res, last_res)
        return None


    def update_virtual_free_space(self, job, alloc):
        """Update the virtual free space after a job has been assigned."""
        first_res, last_res = alloc
        for l in self.virtual_free_space.generator():
            # If the allocated range overlaps with this free space...
            if not (last_res < l.first_res or first_res > l.last_res):
                if first_res <= l.first_res and last_res >= l.last_res:
                    # Entire free space block is used
                    self.virtual_free_space.remove(l)
                elif first_res <= l.first_res:
                    # Top part of free space block is used
                    l.first_res = last_res + 1
                elif last_res >= l.last_res:
                    # Bottom part of free space block is used
                    l.last_res = first_res - 1
                else:
                    # Middle of free space block is used, split it into two
                    new_last_res = l.last_res
                    l.last_res = first_res - 1
                    self.virtual_free_space.insertNewFreeSpaceAfter(last_res + 1, new_last_res, l.length, l)
