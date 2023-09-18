import json
import re

from procset import ProcSet
from itertools import islice

from batsim.batsim import BatsimScheduler

class Fcfs_sched(BatsimScheduler):
    def __init__(self, options):
        super().__init__(options)
        self.logger.info("FCFS with Dependencies init")

    def load_dependencies(self):
        with open("/home/nk/memoria/sched-sim/workloads/hash_dependencies.json", "r") as file:
            self.job_dependencies = json.load(file)
            
        self.job_dependencies = {int(k): v for k, v in self.job_dependencies.items()}

    def onSimulationBegins(self):
        self.nb_completed_jobs = 0
        self.sched_delay = 0.5  # Simulates the time spent by the scheduler to take decisions

        self.open_jobs = []
        self.completed_jobs = set()

        self.computing_machines = ProcSet()
        self.idle_machines = ProcSet((0, self.bs.nb_compute_resources - 1))

        self.load_dependencies()

    def job_is_ready(self, job):
        """Check if all dependencies of the job have been completed."""
        # Extraer el ID del trabajo usando regex
        match = re.search(r'!(\d+)$', job.id)
        if not match:
            print(f"Job {job.id} does not have the expected format.")
            return False  # Si no se encuentra el formato esperado, considerar que el trabajo no está listo
            
        job_id = int(match.group(1))  # Convertir el ID extraído a entero

        # Verificar si el trabajo tiene dependencias en el atributo 'job_dependencies'
        if job_id in self.job_dependencies:
            dependencies_met = [dep for dep in self.job_dependencies[job_id] if dep in self.completed_jobs]
            dependencies_not_met = [dep for dep in self.job_dependencies[job_id] if dep not in self.completed_jobs]

            print(f"Checking job: {job.id}")
            print(f"Dependencies of the job: {self.job_dependencies[job_id]}")
            print(f"Met dependencies: {dependencies_met}")
            print(f"Unmet dependencies: {dependencies_not_met}")

            return len(dependencies_not_met) == 0

        return True  # Si el trabajo no tiene dependencias en 'job_dependencies', considerarlo listo

    def scheduleJobs(self):
        print('\n\nopen_jobs = ', [job.id for job in self.open_jobs])
        print('computingM = ', self.computing_machines)
        print('idleM = ', self.idle_machines)

        scheduled_jobs = []

        # Filter out jobs that are ready to run (all dependencies met)
        ready_jobs = [job for job in self.open_jobs if self.job_is_ready(job)]
        print('ready_jobs can be scheduled! = ', [job.id for job in ready_jobs])

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
        print(f"Job {job.id} submitted")
        if job.requested_resources > self.bs.nb_compute_resources:
            self.bs.reject_jobs([job])  # This job requests more resources than the machine has
        else:
            self.open_jobs.append(job)

    def onJobCompletion(self, job):
        print(f"Job {job.id} completed!")

        # Extraer el ID numérico del trabajo usando regex
        match = re.search(r'!(\d+)$', job.id)
        if match:
            numeric_job_id = int(match.group(1))
            self.completed_jobs.add(numeric_job_id)  # Mark job as completed using the numeric ID
        else:
            print(f"Warning: Job ID {job.id} does not have the expected format.")

        self.idle_machines |= job.allocation
        self.computing_machines -= job.allocation
    
    def onDeadlock(self):
        print("Warning: deadlock detected!")
        self.bs.end_simulation()

    def onNoMoreEvents(self):
        self.scheduleJobs()