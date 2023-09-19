import numpy as np
import pandas as pd
import networkx as nx
import json
from IPython.display import Image as IPImage

class JobGenerator:
    def __init__(self, profiles):
        self.graph = nx.DiGraph()
        self.job_count = 0
        self.profiles = profiles

    def add_job(self, profile_name, subtime=0):
        profile = self.profiles[profile_name]
        resources_required = profile.get('np', 1)
        walltime=profile.get('walltime', (2 * (60 * 60 * 24)))
        self.graph.add_node(self.job_count, 
                            profile=profile_name, 
                            subtime=subtime, 
                            resources_required=resources_required,
                            np=np,
                            walltime=walltime,
                            profile_type=profile_name)  # Añadir el tipo de perfil como atributo
        self.job_count += 1
        return self.job_count - 1

    def add_dependency(self, source, target):
        self.graph.add_edge(source, target)

    def generate_jobs(self, num_jobs, high_load_frequency, dependency_prob=0.3, high_load_dependency_prob=0.7, time_gap=1.0, gap_limits=(0.5, 1.5)):
        current_time = 0
        for _ in range(num_jobs):
            current_time = self._increment_time(current_time, time_gap, gap_limits)
            n_jobs_now, starting_job = self._create_jobs_at_current_time(current_time, high_load_frequency)
            self._add_dependencies(n_jobs_now, starting_job, dependency_prob, high_load_dependency_prob, current_time)
            
        return self.graph

    def _increment_time(self, current_time, time_gap, gap_limits):
        gap = np.random.uniform(*gap_limits)
        return current_time + gap * time_gap

    def _create_jobs_at_current_time(self, current_time, high_load_frequency):
        profile_types = list(self.profiles.keys())
        n_jobs_now = np.random.poisson(lam=high_load_frequency)
        starting_job = self.job_count
        random_profiles = np.random.choice(profile_types, n_jobs_now)
        for p in random_profiles:
            self.add_job(p, subtime=current_time)
        return n_jobs_now, starting_job
    
    def _add_dependencies(self, n_jobs_now, starting_job, dependency_prob, high_load_dependency_prob, current_time):
        current_dependency_prob = dependency_prob if n_jobs_now <= 2 else high_load_dependency_prob
        for job in range(starting_job, self.job_count - 1):
            if np.random.rand() < current_dependency_prob and self.graph.nodes[job]['profile'] != self.graph.nodes[job + 1]['profile']:
                self.add_dependency(job, job + 1)
        if n_jobs_now > 2:
            self._add_cross_dependencies(starting_job, high_load_dependency_prob, current_time)

    def _add_cross_dependencies(self, starting_job, high_load_dependency_prob, current_time):
        profile_types = list(self.profiles.keys())
        cross_dependency_job = self.add_job(np.random.choice(profile_types), subtime=current_time)
        for job in range(starting_job, self.job_count - 1):
            if np.random.rand() < high_load_dependency_prob:
                self.add_dependency(job, cross_dependency_job)
                import json

    def _generate_job_data(self):
        job_data = []
        for node in self.graph.nodes():
            job_info = self.graph.nodes[node]
            
            # Fetch the correct walltime for the profile of the job
            walltime = self.profiles[job_info['profile']]['walltime']

            job = {
                "id": node,
                "profile": job_info['profile'],
                "res": job_info['resources_required'],
                "subtime": job_info['subtime'],
                "walltime": walltime
            }

            # Handling dependencies
            predecessors = list(self.graph.predecessors(node))
            if predecessors:
                job['dependencies'] = predecessors

            job_data.append(job)
        return job_data
    
    def generate_variable_dag(self, duration=60, check_interval=1, arrival_probability=0.3, num_jobs=3):
        # duration: duración total en minutos
        # check_interval: cada cuántos minutos verificar si llega un trabajo
        # arrival_probability: probabilidad de que llegue un trabajo en cada intervalo
        # num_jobs: número de DAGs en cada trabajo generado
        
        # Obtener todos los perfiles disponibles
        load_profiles = list(self.profiles.keys())

        # Lista para almacenar las dependencias cruzadas del primer DAG
        cross_dependencies = []

        current_time = 0  # Iniciar el tiempo actual
        while current_time < duration:
            if np.random.rand() < arrival_probability:
                # Genera el DAG con carga variable
                previous_node = None
                nodes_in_current_dag = []  # Lista para almacenar los nodos del DAG actual
                for i in range(num_jobs):
                    # Selecciona un perfil aleatoriamente para variar la carga
                    profile = np.random.choice(load_profiles)
                    current_node = self.add_job(profile, subtime=current_time + i)

                    # Si hay un nodo anterior, añade una dependencia
                    if previous_node is not None:
                        self.add_dependency(previous_node, current_node)
                    nodes_in_current_dag.append(current_node)
                    previous_node = current_node

                # Añadir dependencias cruzadas
                cross_dependency_profile = np.random.choice(load_profiles)
                cross_dependency_node = self.add_job(cross_dependency_profile, subtime=current_time)
                
                # Si es la primera vez que se genera un DAG, determina las dependencias cruzadas
                if not cross_dependencies:
                    for node in nodes_in_current_dag:
                        # Variar la probabilidad de añadir una dependencia cruzada entre 30% y 70%
                        if np.random.rand() < np.random.uniform(0.3, 0.7):
                            self.add_dependency(node, cross_dependency_node)
                            cross_dependencies.append(node)
                else:
                    # En las siguientes veces, usa las mismas dependencias cruzadas
                    for node_index in cross_dependencies:
                        adjusted_node = node_index + len(self.graph.nodes()) - num_jobs - 1
                        self.add_dependency(adjusted_node, cross_dependency_node)

            current_time += check_interval

    def generate_jobs_json(self, file_name):
        # Generar el archivo workload.json
        data = {
            "command": "autogenerated workload",
            "date": str(np.datetime64('now')),
            "description": "this workload had been automatically generated",
            "profiles_description": "Randomly generated profiles",
            "profiles": self.profiles
        }

        # Determining the maximum number of resources used by any job in the profiles
        data["nb_res"] = max([profile.get('np', 1) for profile in self.profiles.values()])

        jobs = []

        for node in self.graph.nodes():
            job_info = self.graph.nodes[node]
            
            # Fetch the correct walltime for the profile of the job
            walltime = self.profiles[job_info['profile']]['walltime']

            job = {
                "id": node,
                "profile": job_info['profile'],
                "res": job_info['resources_required'],
                "subtime": job_info['subtime'],
                "walltime": job_info['walltime']
            }

            # Handling dependencies
            predecessors = list(self.graph.predecessors(node))
            if predecessors:
                job['dependencies'] = predecessors

            jobs.append(job)
            
        data["jobs"] = jobs

        with open(file_name + '.json', 'w') as file:
            json.dump(data, file, indent=4)

        # Generar el archivo dependencies.json
        dependencies_data = {}
        for node in self.graph.nodes():
            predecessors = list(self.graph.predecessors(node))
            if predecessors:
                dependencies_data[node] = predecessors

        with open(file_name + '_dependencies.json', 'w') as file:
            json.dump(dependencies_data, file, indent=4)

    def generate_jobs_dataframe(self):
        job_data = self._generate_job_data()
        for job in job_data:
            if 'dependencies' in job:
                job['dependencies'] = ", ".join(map(str, job['dependencies']))
            else:
                job['dependencies'] = None

        # Convertir la lista de trabajos en un DataFrame
        df = pd.DataFrame(job_data)
        return df
    
    def visualize_with_dot(self):
        A = nx.nx_agraph.to_agraph(self.graph)
        A.layout(prog='dot')
        A.draw('temp.png')  # Save the visualization in a temporary file
        return IPImage(filename='temp.png')

    def visualize_with_subtime_annotations_dot(self):
        # Crear una copia del grafo para no modificar el original
        graph_copy = self.graph.copy()
        
        # Modificar las etiquetas de los nodos para incluir el subtime
        for node, data in graph_copy.nodes(data=True):
            subtime = data['subtime']
            profile_type = data.get('profile_type', '')  # Use get in case 'profile_type' doesn't exist
            walltime = data.get('walltime', '')  # Use get in case 'walltime' doesn't exist
            graph_copy.nodes[node]['label'] = f"{node}\nsubtime: {subtime}\nprofile_type: {profile_type}\nwalltime: {walltime}"

        # Visualizar con pygraphviz
        A = nx.nx_agraph.to_agraph(graph_copy)
        A.layout(prog='dot')
        A.draw('temp_with_subtime.png')  # Guardar la visualización en un archivo temporal

        # Mostrar la imagen generada
        return IPImage(filename='temp_with_subtime.png')