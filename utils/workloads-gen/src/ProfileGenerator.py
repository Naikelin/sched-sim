import numpy as np
import pandas as pd
import json

MIN_VALUE = 1e7

LOW_CPU_MAX = 1e9
MID_CPU_MAX = 5e9
HIGH_CPU_MAX = 1e11

LOW_COM_MAX = 1e6
MID_COM_MAX = 5e9
HIGH_COM_MAX = 1e11

class ProfileGenerator:
    
    def __init__(self, max_resources=4):
        self.profiles = {}
        # Establecemos el valor de max_resources. Este valor dependerá de la cantidad de recursos disponibles en el sistema, pero debe ser ingresado manualmente.
        self.max_resources = max_resources

    """ 
    Bajo: Si tanto el CPU como el COM están en el rango bajo, entonces la tarea probablemente no necesite muchos recursos.
    Medio: Si el CPU o el COM están en el rango medio, la tarea podría beneficiarse de más recursos. Podemos establecer np en 2 o 3 dependiendo de si uno o ambos valores están en el rango medio.
    Alto: Si tanto el CPU como el COM están en el rango alto, la tarea probablemente necesite muchos recursos.
    """
    def get_np(self, cpu, com):
        # Normalizar los valores al rango [0, 1]
        normalized_cpu = cpu / HIGH_CPU_MAX
        normalized_com = com / HIGH_COM_MAX
        
        # Calcular el score como la media de los valores normalizados
        score = (normalized_cpu + normalized_com) / 2
        
        # Asignar recursos proporcionalmente al score
        resources = int(1 + score * (self.max_resources - 1))
        
        return resources
    
    def compute_walltime(self, cpu, com, np_val):
        # Factor base de tiempo proporcional a la suma de CPU y COM
        base_time = (cpu + com) / (HIGH_CPU_MAX + HIGH_COM_MAX)
        
        # Ajustar el factor base de tiempo por la cantidad de recursos
        # Aquí, 3600 es un factor de escala para convertir el valor en segundos (puede ajustarse según las necesidades)
        walltime = base_time * 3600 / np_val
        
        return walltime

    def generate_profile(self, cpu_range, com_range, profile_prefix):
        cpu = np.random.uniform(*cpu_range)
        com = np.random.uniform(*com_range)
        np_val = self.get_np(cpu, com)
        walltime = self.compute_walltime(cpu, com, np_val)
        profile_name = f"{profile_prefix}_{len(self.profiles) + 1}"
        self.profiles[profile_name] = {
            "type": "parallel_homogeneous",
            "cpu": cpu,
            "com": com,
            "np": np_val,
            "walltime": walltime
        }
        return profile_name

    def generate_low_profile(self):
        return self.generate_profile((1e7, LOW_CPU_MAX), (1024, LOW_COM_MAX), "low")

    def generate_med_profile(self):
        if np.random.choice([True, False]):
            cpu_range = (LOW_CPU_MAX, MID_CPU_MAX)
            com_range = (LOW_COM_MAX, MID_COM_MAX)
        else:
            cpu_range = (MID_CPU_MAX, HIGH_CPU_MAX)
            com_range = (MID_COM_MAX, HIGH_COM_MAX)
        return self.generate_profile(cpu_range, com_range, "med")

    def generate_high_profile(self):
        return self.generate_profile((MID_CPU_MAX, HIGH_CPU_MAX), (MID_COM_MAX, HIGH_COM_MAX), "high")

    def generate(self, number_of_profiles=10, low_percent=0.3, med_percent=0.4, high_percent=0.3):
        assert low_percent + med_percent + high_percent == 1.0
        
        num_low = int(number_of_profiles * low_percent)
        num_med = int(number_of_profiles * med_percent)
        num_high = number_of_profiles - num_low - num_med

        for _ in range(num_low):
            self.generate_low_profile()

        for _ in range(num_med):
            self.generate_med_profile()

        for _ in range(num_high):
            self.generate_high_profile()
        
        return self.profiles
    
    def to_dataframe(self):
        """Convierte los perfiles generados en un DataFrame de pandas."""
        return pd.DataFrame.from_dict(self.profiles, orient='index')

    def to_json(self):
        """Convierte los perfiles generados en una representación JSON."""
        return json.dumps(self.profiles, indent=4)