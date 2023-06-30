from itertools import islice
from procset import ProcSet
from batsim.batsim import BatsimScheduler

class Greedy_sched(BatsimScheduler):

    def onSimulationBegins(self):
        self.nb_completed_jobs = 0
        self.jobs_completed = []
        self.jobs_waiting = []
        self.sched_delay = 0.005
        self.openJobs = set()
        self.availableResources = ProcSet((0,self.bs.nb_compute_resources-1))

    def scheduleJobs(self):
        scheduledJobs = []

        # Ordenar trabajos abiertos por recursos requeridos, de menor a mayor
        sortedJobs = sorted(self.openJobs, key=lambda job: job.requested_resources)

        for job in sortedJobs:
            nb_res_req = job.requested_resources

            if nb_res_req <= len(self.availableResources):
                job_alloc = ProcSet(*islice(self.availableResources, nb_res_req))
                job.allocation = job_alloc
                scheduledJobs.append(job)

                self.availableResources -= job_alloc
                self.openJobs.remove(job)

        self.bs.consume_time(self.sched_delay)

        if len(scheduledJobs) > 0:
            self.bs.execute_jobs(scheduledJobs)

    def onJobSubmission(self, job):
        if job.requested_resources > self.bs.nb_compute_resources:
            self.bs.reject_jobs([job])
        else:
            self.openJobs.add(job)

    def onJobCompletion(self, job):
        self.availableResources |= job.allocation

    def onNoMoreEvents(self):
        self.scheduleJobs()
