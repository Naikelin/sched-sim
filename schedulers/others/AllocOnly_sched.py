import re

from .free_space_container import FreeSpaceContainer
from procset import ProcSet
from sortedcontainers import SortedListWithKey
from pybatsim.batsim.batsim import BatsimScheduler

class AllocOnly_sched(BatsimScheduler):


    """ -------------------
            Constructor
    ------------------- """

    def __init__(self, options):
        super().__init__(options)
        # Options from config file
        self.platform = self.options['platform']
        self.algorithm = self.options['algorithm']
        self.priority_policy = self.options['priority_policy']
        self.optimisation = self.options['optimisation']
        self.progress_bar = self.options['progress_bar']

        # Scheduling variables
        self.listFreeSpace = None
        self.queuedJobs = None
        self.queuedJobsNotReady = None
        self.runningJobs = None
        self.completedJobs = None
        self.rejectedJobs = None

    """ -------------------
        General Methods
    ------------------- """

    def _move_from_not_ready_to_q(self, job):
        """ move job from not ready to queued """
        print(f"[ACTION] Job {job.id} has been moved from not ready to queued.")
        self.queuedJobsNotReady.remove(job)
        self.queuedJobs.append(job)

    def _remove_job_from_running_job(self, job):
        """ remove job from running jobs """
        self.runningJobs.remove(job)

    def _add_to_completed_jobs(self, job):
        """ add job to completed jobs """
        self.completedJobs.append(job)

    def _add_jobs_to_q_if_ready(self):
        """ add jobs to queued if ready """
        for job in self.queuedJobsNotReady:
            if self._check_if_can_schedule(job):
                print(f"[ACTION] Job {job.id} has completed dependencies. Can be Scheduled.")
                self._move_from_not_ready_to_q(job)

    """ -------------------
            Schedulers
    ------------------- """

    def _scheduler(self, job):
        algorithm = self.algorithm.lower()
        switcher = {
            'fcfs': self._scheduler_FCFS,
            }
        
        # Get the function from switcher dictionary
        func = switcher.get(algorithm)
        if func is None:
            raise ValueError(f"Invalid algorithm: {algorithm}")
        
        # Execute the function
        return func(job)
    
    def _schedule(self):
        algorithm = self.algorithm.lower()
        switcher = {
            'fcfs': self._schedule_FCFS,
            }
        
        # Get the function from switcher dictionary
        func = switcher.get(algorithm)
        if func is None:
            raise ValueError(f"Invalid algorithm: {algorithm}")
        
        # Execute the function
        return func()

    def _scheduler_FCFS(self, job):
        
        """ if dependencies are not met, add to queued not ready jobs """
        if not self._check_if_can_schedule(job):
            self.queuedJobsNotReady.append(job)
        else :
            """ if job is ready, add on queued jobs it """
            #print(f"Job {job.id} on queued jobs")
            self.queuedJobs.append(job)

        """ schedule jobs """
        self._schedule()
    
    def _schedule_FCFS(self):
        current_time = self.bs.time()
        allocs = self.allocHeadOfList(current_time)
        
        if len(allocs) > 0:
            jobs = []
            for (job, (first_res, last_res)) in allocs:
                job.allocation = ProcSet((first_res, last_res))
                jobs.append(job)
            print(f"[SCHEDULED] Schedule jobs: {jobs}")
            self.bs.execute_jobs(jobs)

    def allocHeadOfList(self, current_time):
        allocs = []
        while len(self.queuedJobs) > 0:
            alloc = self.allocJobFCFS(self.queuedJobs[0], current_time)
            if alloc is None:
                break
            job = self.queuedJobs.pop(0)
            job.start_time = current_time
            job.estimate_finish_time = job.requested_time + job.start_time
            self.runningJobs.add(job)
            allocs.append((job, alloc))
        return allocs

    def allocJobFCFS(self, job, current_time):
        for l in self.listFreeSpace.generator():
            if job.requested_resources <= l.res:
                alloc = self.listFreeSpace.assignJob(l, job, current_time)
                return alloc
        return None
    
    """ -------------------
        pyBatsim Methods 
    ------------------- """

    def onAfterBatsimInit(self):
        # List of free spaces containers
        self.listFreeSpace = FreeSpaceContainer(self.bs.nb_resources)
        # Queued Jobs
        self.queuedJobs = []
        # Queued Jobs not ready cause of dependencies
        self.queuedJobsNotReady = []
        # Running Jobs
        self.runningJobs = SortedListWithKey(key=lambda x: x.requested_resources)
        # Completed Jobs
        self.completedJobs = []
        # Rejected Jobs
        self.rejectedJobs = []

    def onJobSubmission(self, job):    
        print (f"[SUBMIT] {job}")
        self._scheduler(job)

    def onJobCompletion(self, job):
        print (f"[COMPLETED] {job}")
        current_time = self.bs.time()

        # Remove job from free space
        self.listFreeSpace.unassignJob(job)

        # Remove job from running jobs
        self._remove_job_from_running_job(job)

        # Check if job has not completed dependencies
        job.finish_time = current_time
        self._add_to_completed_jobs(job)

        # Schedule jobs
        self._add_jobs_to_q_if_ready()
        self._schedule()


    """ -------------------
            Utils 
    ------------------- """

    def _get_id_from_job(self, job) -> int:
        """ get job id from job. if not found return -1 """
        job_to_sintrg = str(job)
        match = re.search(r'w\d+!(\d+);', job_to_sintrg)
        if match:
            job_id = int(match.group(1))
            return job_id
        return -1

    def _check_if_can_schedule(self, job):
        """ check if job has not completed dependencies """
        jobs_completed_ids = [self._get_id_from_job(j) for j in self.completedJobs]
        job_dep_ids = [j for j in job.dependencies]
    
        return all(elem in jobs_completed_ids for elem in job_dep_ids)

    def _check_if_need_to_be_remove(self, job):
        """ check if job dependencies has been removed in rejected jobs """
        for d in job.dep:
            if d in self.rejectedJobs:
                return True
        return False