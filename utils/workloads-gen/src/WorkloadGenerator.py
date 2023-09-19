from JobGenerator import JobGenerator
from ProfileGenerator import ProfileGenerator 
import json

if __name__ == '__main__':
    prof_gen = ProfileGenerator(max_resources=4)
    # Generar perfiles
    number_of_profiles = 50
    profiles = prof_gen.generate(number_of_profiles, low_percent=0.3, med_percent=0.7, high_percent=0)

    # Generar trabajos
    job_gen = JobGenerator(profiles)
    job_gen.generate_variable_dag(duration=60, check_interval=1, arrival_probability=0.3, num_jobs=3)

    job_gen.generate_jobs_json('workload')