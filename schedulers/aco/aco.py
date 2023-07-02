import random
from procset import ProcSet
from batsim.batsim import BatsimScheduler
import threading
import time

class Aco(BatsimScheduler):

    def onSimulationBegins(self):
        self.nb_completed_jobs = 0
        self.jobs_completed = []
        self.jobs_waiting = []
        self.sched_delay = 0.005
        self.openJobs = [] 
        self.availableResources = ProcSet((0, self.bs.nb_compute_resources - 1))
        self.pheromone = {}
        self.pheromone_initial = 1
        self.evaporation_rate = 0.5
        self.exploration_param = 0.5
        self.ant_count = 1
        self.ants_solutions = [[] for _ in range(self.ant_count)]  # Inicializa con listas vacías
        self.semaphore = threading.Semaphore()

        
    def initializePheromone(self):
        for job in self.openJobs:
            self.pheromone[job.id] = {}
            for resource in self.availableResources:
                self.pheromone[job.id][resource] = self.pheromone_initial

    def updatePheromone(self, solutions):
        self.semaphore.acquire()
        merit_sum = sum([self.calculateMerit(solution) for solution in solutions])
        evaporation_rate = 0.5  # Factor de evaporación

        for solution in solutions:
            merit = self.calculateMerit(solution)
            for index, resource in enumerate(solution):
                if index < len(self.openJobs):  # Verificar si el índice es válido
                    job = self.openJobs[index]  # Obtener trabajo por índice

                    # Actualizar las feromonas del recurso
                    self.pheromone[resource] = self.pheromone.get(resource, 1) + (merit / merit_sum) - evaporation_rate

        # Imprimir las feromonas después de la actualización
        print(f"Pheromones after update: {self.pheromone}")

    def evaporatePheromone(self):
        for job in self.openJobs:
            for resource in self.availableResources:
                self.pheromone[job.id][resource] *= self.evaporation_rate

    def antSearch(self, ant_index, time_limit, max_iterations):
        start_time = time.time()
        iteration = 0

        solution = []

        for job in self.openJobs:
            if time.time() - start_time > time_limit or iteration >= max_iterations:
                break

            if random.uniform(0, 1) < self.exploration_param:
                resource = random.choice(list(self.availableResources))
            else:
                resource_pheromones = [(r, self.pheromone.get(job.id, {}).get(r, self.pheromone_initial)) for r in self.availableResources]
                resource, _ = max(resource_pheromones, key=lambda x: x[1])

            solution.append(resource)
            print(f"Ant {ant_index} [{iteration}] generated solution: {solution}")
            iteration += 1

        self.ants_solutions[ant_index] = solution
        print(f"Ant {ant_index} generated solution: {solution}")

    def calculateMerit(self, solution):
        if solution is None:  # Verifica si la solución es None
            return 0
        
        merit = 0
        for index, resource in enumerate(solution):
            if index < len(self.openJobs):  # Verificar si el índice es válido
                job = self.openJobs[index]  # Obtener trabajo por índice

                # Supongamos que tienes una función `calculate_completion_time(job, resource)` que 
                # calcula el tiempo de finalización para un trabajo dado en un recurso específico
                # Aquí simplemente simulo esto con un número aleatorio
                completion_time = random.uniform(0, 10)

                # El mérito es mayor si el tiempo de finalización es menor
                merit += 1 / completion_time
            else:
                break  # Salir del bucle si no hay más trabajos abiertos
        return merit

    def calculateMerit(self, solution):
        merit = 0
        for resource in solution:
            if self.openJobs:  # Verificar si hay trabajos abiertos
                job = self.openJobs.pop(0)  # Obtener el primer trabajo de la lista
                # Realizar el cálculo del mérito para el trabajo y recurso correspondiente
                # Aquí puedes agregar tu lógica de cálculo del mérito
                merit += 1  # Ejemplo: simplemente incrementar el mérito en 1
            else:
                break  # Salir del bucle si no hay más trabajos abiertos
        return merit


    def scheduleJobs(self):
        time_limit = 1  # segundos, puedes ajustar este valor
        max_iterations = 10  # número máximo de iteraciones que una hormiga puede hacer, puedes ajustar este valor

        threads = []
        for ant_index in range(self.ant_count):
            print(f"Starting ant {ant_index}")
            thread = threading.Thread(target=self.antSearch, args=(ant_index, time_limit, max_iterations))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        self.updatePheromone(self.ants_solutions)



    def selectResources(self, job):
        pheromone_values = [self.pheromone.get(job.id, {}).get(resource, self.pheromone_initial) for resource in self.availableResources]

        if job.requested_resources > len(self.availableResources):
            return None

        # Ordenamos los recursos disponibles según sus feromonas (en orden descendente)
        available_resources_list = sorted(self.availableResources, key=lambda x: self.pheromone.get(job.id, {}).get(x, self.pheromone_initial), reverse=True)
        
        # Seleccionamos los primeros recursos 'requested_resources'
        selected_resources = available_resources_list[:job.requested_resources]

        job_alloc = ProcSet(*selected_resources)

        if len(job_alloc) != job.requested_resources:
            print(f"Error: Job {job.id} requested {job.requested_resources} resources, but only {len(job_alloc)} were assigned.")

        return job_alloc


    def onJobSubmission(self, job):
        if job.requested_resources > self.bs.nb_compute_resources:
            self.bs.reject_jobs([job])
        else:
            self.openJobs.append(job)

    def onJobCompletion(self, job):
        self.availableResources |= job.allocation

    def onNoMoreEvents(self):
        self.scheduleJobs()
