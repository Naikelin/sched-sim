# python imports
import re

# external imports
from scipy.optimize import dual_annealing
import pyswarms as ps
import numpy as np

# internal imports
from free_space_container import FreeSpaceContainer
from procset import ProcSet
from sortedcontainers import SortedListWithKey
from pybatsim.batsim.batsim import BatsimScheduler
from sim_with_q import SimWithQ

INFINITY = float("inf")

class AllocOnly_sched(BatsimScheduler):


    """ -------------------
            Constructor
    ------------------- """

    def __init__(self, options):
        super().__init__(options)
        # Options from config file
        self.platform = self.options['platform']
        self.algorithm = self.options['algorithm']
        self.optimisation : bool = self.options.get('optimisation', False)
        self.optimisation_type = self.options.get('optimisation_type', '')
        self.progress_bar = self.options['progress_bar']
        self.optimisation_confs = self.options.get('optimisation_confs', {})

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
            'sjf': self._scheduler_SJF,
            'easy-backfill': self._scheduler_EASY_Backfill,
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
            'sjf': self._schedule_SJF,
            'easy-backfill': self._schedule_EASY_Backfill,
            }
        
        # Get the function from switcher dictionary
        func = switcher.get(algorithm)
        if func is None:
            raise ValueError(f"Invalid algorithm: {algorithm}")
        
        # Execute the function
        return func()
    
    def _optimizer(self):
        algorithm = self.optimisation_type.lower()
        switcher = {
            'hill-climbing': self.hill_climbing_optimize,
            'simulated-annealing': self.simulated_annealing_optimize,
            'pso': self.pso_optimize,
            }
        
        # Get the function from switcher dictionary
        func = switcher.get(algorithm)
        if func is None:
            raise ValueError(f"Invalid algorithm: {algorithm}")
        
        # Execute the function
        return func()
    
    """ -------------------
            FCFS
    ------------------- """

    def _scheduler_FCFS(self, job):
        
        """ if dependencies are not met, add to queued not ready jobs """
        if not self._check_if_can_schedule(job):
            self.queuedJobsNotReady.append(job)
        else :
            """ if job is ready, add on queued jobs it """
            #print(f"Job {job.id} on queued jobs")
            self.queuedJobs.append(job)

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

    def allocJobFCFS(self, job, current_time):
        for l in self.listFreeSpace.generator():
            if job.requested_resources <= l.res:
                alloc = self.listFreeSpace.assignJob(l, job, current_time)
                return alloc
        return None
    
    """ -------------------
            SJF
    ------------------- """
    
    def _scheduler_SJF(self, job):
        """ if dependencies are not met, add to queued not ready jobs """
        if not self._check_if_can_schedule(job):
            self.queuedJobsNotReady.append(job)
        else:
            """ if job is ready, add on queued jobs sorted by requested time """
            self._insert_sorted_by_duration(job)

    def _schedule_SJF(self):
        current_time = self.bs.time()
        allocs = self.allocHeadOfList(current_time)
        
        if len(allocs) > 0:
            jobs = []
            for (job, (first_res, last_res)) in allocs:
                job.allocation = ProcSet((first_res, last_res))
                jobs.append(job)
            print(f"[SCHEDULED] Schedule jobs: {jobs}")
            self.bs.execute_jobs(jobs)

    def _insert_sorted_by_duration(self, job):
        """ Insert job into queuedJobs in a sorted manner (shortest jobs first) """
        index = 0
        while index < len(self.queuedJobs) and self.queuedJobs[index].requested_time <= job.requested_time:
            index += 1
        self.queuedJobs.insert(index, job)
    
    """ -------------------
        EASY-Backfill
    ------------------- """

    def _scheduler_EASY_Backfill(self, job):
        """ if dependencies are not met, add to queued not ready jobs """
        if not self._check_if_can_schedule(job):
            self.queuedJobsNotReady.append(job)
        else :
            """ if job is ready, add on queued jobs it """
            #print(f"Job {job.id} on queued jobs")
            self.queuedJobs.append(job)

    def _schedule_EASY_Backfill(self):
        current_time = self.bs.time()
        allocs = self.allocHeadOfList(current_time)

        if len(self.queuedJobs) > 1:
            first_job = self.queuedJobs.pop(0)
            allocs += self.allocBackFill(first_job, current_time)
            self.queuedJobs.insert(0, first_job)

        if len(allocs) > 0:
            jobs = []
            for (job, (first_res, last_res)) in allocs:
                job.allocation = ProcSet((first_res, last_res))
                jobs.append(job)
            self.bs.execute_jobs(jobs)

    def allocJobBackfill(self, job, current_time):
        for l in self.listFreeSpace.generator():
            if job.requested_resources <= l.res and job.requested_time <= l.length:
                alloc = self.listFreeSpace.assignJob(l, job, current_time)
                return alloc
        return None
    
    def findAllocFuture(self, job):
        listFreeSpaceTemp = self.listFreeSpace.copy()
        for j in self.runningJobs:
            new_free_space_created_by_this_unallocation = listFreeSpaceTemp.unassignJob(
                j)
            if job.requested_resources <= new_free_space_created_by_this_unallocation.res:
                alloc = listFreeSpaceTemp.assignJob(
                    new_free_space_created_by_this_unallocation, job, j.estimate_finish_time)
                # we find a valid allocation
                return (alloc, j.estimate_finish_time)
        # if we are it means that the job will never fit in the cluster!
        assert False
        return None
    
    def allocFutureJob(self, first_job_res, first_job_starttime, current_time):
        """
        Update self.listFreeSpace to insert (if needed) 2 virtual free space.
        These freespaces need to be removes afterwards Example: 3 machine
        (A,B,C), 1 job running (1), the firstjob is 2
        A|
        B|     22
        C|1111122
        -'------------>
        A FreeSpace (A,B, INFINITY) exists, we replace it with 2 FreeSpaces
        (A,A, INFINITY) and (A,B,first_job_starttime)

        These 2 new FreeSpaces are "linked", in order to modify one freeSpace
        when the other is modified.
        """
        first_virtual_space = None
        first_shortened_space = None
        second_virtual_space = None
        second_shortened_space = None
        for l in self.listFreeSpace.generator():
            if l.first_res == first_job_res[0]:
                assert first_virtual_space is None and first_shortened_space is None

                first_shortened_space = l
                l.length = first_job_starttime - current_time

            elif l.first_res < first_job_res[0] and l.last_res >= first_job_res[0]:
                # we transform this free space as 2 free spaces, the wider
                # rectangle and the longest rectangle
                assert first_virtual_space is None and first_shortened_space is None

                first_virtual_space = self.listFreeSpace.insertNewFreeSpaceAfter(
                    l.first_res, first_job_res[0] - 1, INFINITY, l)

                first_virtual_space.linkedTo = l
                l.linkedTo = first_virtual_space

                first_virtual_space.allocSmallestResFirst = True
                l.allocSmallestResFirst = False

                first_shortened_space = l
                l.length = first_job_starttime - current_time

            if l.last_res == first_job_res[-1]:
                assert second_virtual_space is None and second_shortened_space is None

                second_shortened_space = l
                l.length = first_job_starttime - current_time
            elif l.first_res <= first_job_res[-1] and l.last_res > first_job_res[-1]:
                # we transform this free space as 2 free spaces, the wider
                # rectangle and the longest rectangle
                assert second_virtual_space is None and second_shortened_space is None

                second_virtual_space = self.listFreeSpace.insertNewFreeSpaceAfter(
                    first_job_res[-1] + 1, l.last_res, INFINITY, l)

                second_virtual_space.linkedTo = l
                l.linkedTo = second_virtual_space

                second_virtual_space.allocSmallestResFirst = False
                l.allocSmallestResFirst = True

                second_shortened_space = l
                l.length = first_job_starttime - current_time
                # no need to continue
                break
        return (first_virtual_space, first_shortened_space,
                second_virtual_space, second_shortened_space)
    
    def findBackfilledAllocs(self, current_time, first_job_starttime):
        allocs = []
        jobsToRemove = []
        for j in self.queuedJobs:
            alloc = self.allocJobBackfill(j, current_time)
            if alloc is not None:
                allocs.append((j, alloc))
                j.start_time = current_time
                j.estimate_finish_time = j.requested_time + j.start_time
                jobsToRemove.append(j)
                self.runningJobs.add(j)

        for j in jobsToRemove:
            self.queuedJobs.remove(j)

        return allocs
    
    def allocBackFill(self, first_job, current_time):

        (first_job_res, first_job_starttime) = self.findAllocFuture(first_job)

        (first_virtual_space, first_shortened_space, second_virtual_space,
         second_shortened_space) = self.allocFutureJob(first_job_res,
                                                       first_job_starttime,
                                                       current_time)

        allocs = self.findBackfilledAllocs(current_time, first_job_starttime)

        if first_virtual_space is not None:
            del first_virtual_space.linkedTo.linkedTo
            del first_virtual_space.linkedTo
            if not hasattr(first_virtual_space, "removed"):
                self.listFreeSpace.remove(first_virtual_space)
        if first_shortened_space is not None:
            first_shortened_space.length = INFINITY
            first_shortened_space.allocSmallestResFirst = True
        if second_virtual_space is not None:
            del second_virtual_space.linkedTo.linkedTo
            del second_virtual_space.linkedTo
            if not hasattr(second_virtual_space, "removed"):
                self.listFreeSpace.remove(second_virtual_space)
        if second_shortened_space is not None:
            second_shortened_space.length = INFINITY
            second_shortened_space.allocSmallestResFirst = True

        return allocs

    def assert_listFreeSpace_listRunningJob(self):
        len_fp = sum(l.res for l in self.listFreeSpace.generator())
        len_rj = sum(j.requested_resources for j in self.runningJobs)
        assert len_fp + len_rj == self.bs.nb_resources, "INCOHERENT freespaces:" + \
            str(len_fp) + " jobs:" + str(len_rj) + \
            " tot:" + str(self.bs.nb_resources)
    
    """ -------------------
            Others
    ------------------- """
    
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
        
        if self.optimisation:
            """ optimize jobs """
            self._optimizer()

        """ schedule jobs """
        self._schedule()
    

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
    
    """ -------------------
            Optimizers
    ------------------- """
    
    def hill_climbing_optimize(self):
        """Optimize the order of jobs in queuedJobs using Hill Climbing."""
        current_solution = self.queuedJobs[:]
        current_quality = self.evaluate_solution(current_solution)

        improved = True
        while improved:
            improved = False
            neighbors = self.generate_neighbors(current_solution)

            for neighbor in neighbors:
                quality = self.evaluate_solution(neighbor)
                if quality < current_quality:
                    current_quality = quality
                    current_solution = neighbor
                    improved = True
                    break

        self.queuedJobs = current_solution

    def evaluate_solution(self, solution):
        """Evaluate the quality of a solution using the JobSchedulerSimulator."""
        simulator = SimWithQ(self.listFreeSpace, solution)
        total_completion_time = simulator.simulate()
        
        return total_completion_time

    def generate_neighbors(self, solution):
        """Generate neighboring solutions by swapping two jobs."""
        neighbors = []
        for i in range(len(solution)):
            for j in range(i+1, len(solution)):
                neighbor = solution[:]
                neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
                neighbors.append(neighbor)
        return neighbors

    def simulated_annealing_optimize(self):
        """Optimize the order of jobs in queuedJobs using Dual Annealing."""
        if len(self.queuedJobs) < 2:
            return

        # Definir la función objetivo para el optimizador
        def objective(order):
            # Convertir los valores continuos a un orden de trabajos
            sorted_order = sorted(range(len(order)), key=lambda k: order[k])
            solution = [self.queuedJobs[i] for i in sorted_order]
            return self.evaluate_solution(solution)

        # Definir los límites para el optimizador
        num_jobs = len(self.queuedJobs)
        bounds = [(0, 1) for _ in range(num_jobs)]

        # Initial solution (current order)
        init_solution = list(range(num_jobs))

        # Aplicar el dual annealing
        result = dual_annealing(
            objective,
            bounds=bounds,
            x0=init_solution,
            maxiter=self.optimisation_confs.get('maxiter', 500),
            no_local_search=self.optimisation_confs.get('no_local_search', False),
            seed=self.optimisation_confs.get('seed', None),
        )

        # Actualizar queuedJobs con la solución óptima
        sorted_order = sorted(range(len(result.x)), key=lambda k: result.x[k])
        self.queuedJobs = [self.queuedJobs[i] for i in sorted_order]

    def pso_optimize(self):
        """Optimize the order of jobs in queuedJobs using Particle Swarm Optimization."""
        
        if len(self.queuedJobs) < 2:
            return
        
        # Definir la función objetivo para el optimizador
        def objective(order):
            # Redondea y verifica los límites
            rounded_order = np.round(order)  # Utiliza numpy para redondear cada elemento
            print(rounded_order)
            indices = [min(max(0, int(i)), len(self.queuedJobs)-1) for i in rounded_order.ravel()]
            solution = [self.queuedJobs[idx] for idx in indices]
            return self.evaluate_solution(solution)


        # Definir los límites para el optimizador
        num_jobs = len(self.queuedJobs)
        bounds = (np.zeros(num_jobs), np.ones(num_jobs) * (num_jobs - 1))

        # Configurar y ejecutar el PSO
        options = {'c1': 0.5, 'c2': 0.3, 'w':0.9}
        optimizer = ps.single.GlobalBestPSO(n_particles=10, dimensions=num_jobs, options=options, bounds=bounds)
        cost, pos = optimizer.optimize(objective, iters=1000)  # Puedes ajustar iters según tus necesidades
        
        # Actualizar queuedJobs con la solución óptima
        optimized_order = [int(i) for i in pos]
        self.queuedJobs = [self.queuedJobs[i] for i in optimized_order]