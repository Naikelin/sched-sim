from itertools import islice

from procset import ProcSet

from pybatsim.batsim.batsim import BatsimScheduler


class FillerSchedWithEvents(BatsimScheduler):

    def __init__(self, options):
        super().__init__(options)


    def onSimulationBegins(self):
        self.jobs_waiting = [] # List of jobs waiting to be scheduled

        self.sched_delay = 0.005

        self.openJobs = set()
        self.availableResources = ProcSet((0,self.bs.nb_compute_resources-1)) # The machines not running resources nor marked unavailable
        self.unavailableResources = ProcSet() # The resources marked as unavailable by external events
        self.runningResources = ProcSet() # The resources running jobs


    def scheduleJobs(self):
        scheduledJobs = []

        #print('openJobs = ', self.openJobs)
        #print('available = ', self.availableResources)

        # Iterating over a copy to be able to remove jobs from openJobs at traversal
        for job in set(self.openJobs):
            nb_res_req = job.requested_resources

            if nb_res_req <= len(self.availableResources):
                # Retrieve the *nb_res_req* first availables resources
                job_alloc = ProcSet(*islice(self.availableResources, nb_res_req))
                job.allocation = job_alloc
                scheduledJobs.append(job)

                self.availableResources -= job_alloc
                self.runningResources |= job_alloc

                self.openJobs.remove(job)

        # update time
        self.bs.consume_time(self.sched_delay)

        # send to uds
        if len(scheduledJobs) > 0:
            self.bs.execute_jobs(scheduledJobs)

        #print('openJobs = ', self.openJobs)
        #print('available = ', self.availableResources)
        #print('')

    def onJobSubmission(self, job):
        if job.requested_resources > self.bs.nb_compute_resources:
            self.bs.reject_jobs([job]) # This job requests more resources than the machine has
        else:
            self.openJobs.add(job)

    def onJobCompletion(self, job):
        # Resources used by the job and that are unavailable should not be added to available resources
        p = job.allocation - self.unavailableResources
        self.availableResources |= p
        self.runningResources -= job.allocation

    def onNotifyEventMachineUnavailable(self, machines):
        self.unavailableResources |= machines
        self.availableResources -= machines

    def onNotifyEventMachineAvailable(self, machines):
        self.unavailableResources -= machines
        p = machines - self.runningResources # Don't mark as available the resources running a job
        self.availableResources |= p

    def onNotifyGenericEvent(self, event_data):
        pass

    def onNoMoreExternalEvents(self):
        # There are no more external event, reject the jobs that cannot be scheduled due to lack of available resources
        nb_max_available_resources = self.bs.nb_compute_resources - len(self.unavailableResources)
        jobs_to_reject = []
        for job in self.jobs_waiting:
            if job.requested_resources > nb_max_available_resources:
                jobs_to_reject.append(job)

        if len(jobs_to_reject) > 0:
            self.bs.reject_jobs(jobs_to_reject)


    def onNoMoreEvents(self):
        self.scheduleJobs()
