from procset import ProcSet
from itertools import islice

from batsim.batsim import BatsimScheduler

class Fcfs_sched(BatsimScheduler):
    def __init__(self, options):
        super().__init__(options)
        self.logger.info("FCFS with Dependencies init")

    def onSimulationBegins(self):
        self.nb_completed_jobs = 0
        self.sched_delay = 0.5  # Simulates the time spent by the scheduler to take decisions

        self.open_jobs = []
        self.completed_jobs = set()

        self.computing_machines = ProcSet()
        self.idle_machines = ProcSet((0, self.bs.nb_compute_resources - 1))

    def job_is_ready(self, job):
        """Check if all dependencies of the job have been completed."""
        if hasattr(job, 'dependencies'):
            return all(dep in self.completed_jobs for dep in job.dependencies)
        return True  # If job doesn't have dependencies, consider it ready

    def scheduleJobs(self):
        print('\n\nopen_jobs = ', [job.id for job in self.open_jobs])
        print('computingM = ', self.computing_machines)
        print('idleM = ', self.idle_machines)

        scheduled_jobs = []

        # Filter out jobs that are ready to run (all dependencies met)
        ready_jobs = [job for job in self.open_jobs if self.job_is_ready(job)]

        for job in ready_jobs:
            nb_res_req = job.requested_resources

            # Job fits now -> allocation
            if nb_res_req <= len(self.idle_machines):
                res = ProcSet(*islice(self.idle_machines, nb_res_req))
                job.allocation = res
                scheduled_jobs.append(job)
                print(f"Job {job.id} is scheduled!")

                self.computing_machines |= res
                self.idle_machines -= res
                self.open_jobs.remove(job)

        # Update time
        self.bs.consume_time(self.sched_delay)

        # Send decision to batsim
        self.bs.execute_jobs(scheduled_jobs)

    def onJobSubmission(self, job):
        if job.requested_resources > self.bs.nb_compute_resources:
            self.bs.reject_jobs([job])  # This job requests more resources than the machine has
        else:
            self.open_jobs.append(job)

    def onJobCompletion(self, job):
        self.idle_machines |= job.allocation
        self.computing_machines -= job.allocation
        self.completed_jobs.add(job.id)  # Mark job as completed

    def onNoMoreEvents(self):
        self.scheduleJobs()


