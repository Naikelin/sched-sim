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
            if job.requested_resources <= l.res and job.requested_time <= l.length:
                first_res = l.first_res
                last_res = l.first_res + job.requested_resources - 1
                return (first_res, last_res)
        return None

    def update_virtual_free_space(self, job, alloc):
        """Update the virtual free space after a job has been assigned."""
        first_res, last_res = alloc
        self.virtual_free_space.remove((first_res, last_res))