import argparse
from JobGenerator import JobGenerator
from ProfileGenerator import ProfileGenerator
import json

def main(args):
    prof_gen = ProfileGenerator(max_resources=args.max_resources)
    if args.load_profiles:
        with open(args.load_profiles, 'r') as f:
            json_str = f.read()
            profiles = prof_gen.load_from_json(json_str)
    else:
        profiles = prof_gen.generate(args.number_of_profiles, low_percent=args.low_percent, med_percent=args.med_percent, high_percent=args.high_percent)

    job_gen = JobGenerator(profiles)
    job_gen.generate_variable_dag(duration=args.duration, check_interval=args.check_interval, arrival_probability=args.arrival_probability, num_jobs=args.num_jobs)
    job_gen.generate_jobs_json(args.output)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generador de workloads para Batsim")
    parser.add_argument('--max-resources', type=int, default=4, help="Máximo de recursos (máquinas) para ProfileGenerator")
    parser.add_argument('--number-of-profiles', type=int, default=50, help="Número de perfiles a generar")
    parser.add_argument('--low-percent', type=float, default=0.3, help="Porcentaje de perfiles bajos")
    parser.add_argument('--med-percent', type=float, default=0.4, help="Porcentaje de perfiles medios")
    parser.add_argument('--high-percent', type=float, default=0.3, help="Porcentaje de perfiles altos")
    parser.add_argument('--duration', type=int, default=60, help="Duración para generate_variable_dag")
    parser.add_argument('--check-interval', type=int, default=1, help="Intervalo de verificación para generate_variable_dag")
    parser.add_argument('--arrival-probability', type=float, default=0.3, help="Probabilidad de llegada para generate_variable_dag")
    parser.add_argument('--num-jobs', type=int, default=3, help="Número de trabajos para generate_variable_dag")
    parser.add_argument('--output', type=str, default='workload', help="Nombre del archivo de salida para los trabajos generados. Default: workload")
    parser.add_argument('--load-profiles', type=str, help="Ruta del archivo JSON para cargar perfiles")

    args = parser.parse_args()
    main(args)
