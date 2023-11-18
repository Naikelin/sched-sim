import os
import json

# Function to generate YAML and JSON configurations
def generate_configs(algorithms, optimizations):
    yaml_template = """batcmd: batsim -p platforms/small_platform.xml -w workloads/workload.json -e output/{algorithm}{opt}/{algorithm}{opt}
failure-timeout: 5
output-dir: output/{algorithm}{opt}/{algorithm}{opt}
ready-timeout: 10
schedcmd: python -m pybatsim --options-file configs/{algorithm}{opt}.json schedulers/AllocOnly_sched.py
simulation-timeout: 604800
success-timeout: 3600
"""

    json_template = {
        "platform": "platforms/small_platform.yaml",
        "algorithm": "",
        "progress_bar": True,
        "optimisation": False,
        "optimisation_type": "",
        "optimisation_confs": {
            "no_local_search": False
        }
    }

    optimization_switcher = {
        'hc': 'hill-climbing',
        'sa': 'simulated-annealing',
        'sa-opt': 'simulated-annealing-optimized',
        'pso': 'pso'
    }

    algorithm_switcher = {
        'fcfs': 'FCFS',
        'sjf': 'SJF',
        'easy-backfill': 'EASY-BACKFILL'
    }

    # Create 'output' and 'configs' directories
    os.makedirs('output', exist_ok=True)
    os.makedirs('configs', exist_ok=True)

    for alg in algorithms:
        for opt in optimizations:
            opt_suffix = f"-{opt}" if opt else ""
            yaml_content = yaml_template.format(algorithm=alg, opt=opt_suffix)
            yaml_file_name = f"{alg}{opt_suffix}.yaml"

            # Write the YAML content to the file
            with open(f'output/{yaml_file_name}', 'w') as yaml_file:
                yaml_file.write(yaml_content)

            # Update JSON template data
            json_content = json_template.copy()
            json_content["algorithm"] = algorithm_switcher.get(alg, alg.upper())
            json_content["optimisation"] = bool(opt)
            json_content["optimisation_type"] = optimization_switcher.get(opt, "")

            # If the optimization is "sa-opt", set "no_local_search" to True
            if opt == "sa-opt":
                json_content["optimisation_confs"]["no_local_search"] = True

            json_file_name = f"{alg}{opt_suffix}.json"
            # Write the JSON content to the file
            with open(f'configs/{json_file_name}', 'w') as json_file:
                json.dump(json_content, json_file, indent=4)

# Define the algorithms and optimizations
algorithms = ['fcfs', 'sjf', 'easy-backfill']
optimizations = ['hc', 'sa', 'sa-opt', 'pso', '']

# Call the function to generate the configurations
generate_configs(algorithms, optimizations)

# Inform the user that the files have been created
print("YAML and JSON configurations have been generated in the 'output' and 'configs' directories respectively.")

