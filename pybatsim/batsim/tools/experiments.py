"""
    batsim.tools.experiments
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Tools to launch experiments.
"""

import subprocess
import os
import os.path
import sys
import json
import time
import signal
import functools

from pybatsim.batsim.network import NetworkHandler


def is_executable(file):
    return os.access(file, os.X_OK)


def get_value(options, keys, fallback_keys=None, default=None):
    original_options = options

    if not isinstance(keys, list):
        keys = [keys]

    try:
        for k in keys:
            options = options[k]
    except KeyError:
        if fallback_keys:
            return get_value(original_options, fallback_keys, default=default)
        elif default is not None:
            return default
        else:
            print(
                "Option is missing in experiment settings ({})".format(
                    ".".join(keys)),
                file=sys.stderr)
            sys.exit(1)
    return options


def delete_key(options, keys):
    if not isinstance(keys, list):
        keys = [keys]

    try:
        for k in keys[:-1]:
            options = options[k]
        del options[keys[-1]]
    except KeyError:
        pass


def tail(f, n):
    return subprocess.check_output(["tail", "-n", str(n), f]).decode("utf-8")


def truncate_string(s, len_s=30):
    if len(s) > len_s:
        return "..." + s[len(s) - len_s:]
    return s


def get_terminal_size():
    try:
        rows, columns = subprocess.check_output(["stty", "size"]).split()
        return int(rows), int(columns)
    except Exception:
        return None, None


def print_separator(header=None):
    rows, columns = get_terminal_size()
    columns = columns or 30
    if header:
        header = truncate_string(header, columns // 3)
        header = " " + header + " "
        rem_line_len_part = (columns - len(header)) // 2
        line = ("".ljust(rem_line_len_part, "=") +
                header +
                "".ljust(rem_line_len_part, "="))
    else:
        line = "".ljust(columns, "=")
    print(line)


def check_print(header, s):
    if s:
        print_separator(header)
        print(s)


def execute_cl(
        name,
        cl,
        stdout=None,
        stderr=None,
        on_failure=None,
        verbose=False):
    if verbose:
        print("Starting: {}".format(" ".join(cl)), end="")
        if stdout:
            print(" 1>{}".format(stdout.name), end="")
        if stderr:
            print(" 2>{}".format(stderr.name), end="")
        print()

    exec = subprocess.Popen(
        cl, stdout=stdout, stderr=stderr)
    exec.name = name
    return exec



def terminate_cl(p, terminate=False):
    try:
        print("Terminating {}".format(p.name), file=sys.stderr)
    except AttributeError:
        print("Terminating subprocess", file=sys.stderr)
    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
    p.wait()
    if terminate:
        sys.exit(3)


def run_workload_script(options, verbose):
    script = options["batsim"]["workload-script"]["path"]
    interpreter = options["batsim"]["workload-script"].get("interpreter", None)
    args = [str(s) for s in options["batsim"]
            ["workload-script"].get("args", [])]

    def do_run_script(cmds):
        out_workload_file_path = os.path.join(
            options["output-dir"], "workload.json")
        with open(out_workload_file_path, "w") as f:
            script_exec = execute_cl(script, cmds, stdout=f, verbose=verbose)
            ret = script_exec.wait()
            if ret != 0:
                raise ValueError(
                    "Workload script {} failed with return code {}".format(
                        script, ret))
        return out_workload_file_path

    if not os.path.exists(script):
        raise ValueError("Workload script {} does not exist".format(script))

    if interpreter:
        return do_run_script([interpreter, script] + args)
    else:
        if is_executable(script):
            return do_run_script(["./" + script] + args)
        elif script.endswith(".py"):
            return do_run_script(["python3", script] + args)
        else:
            raise ValueError(
                "Workload script {} is not executable but also does not seem to be a python script.".format(script))


def generate_config(options):
    out_config_file_path = os.path.join(
        options["output-dir"], "config.json")
    with open(out_config_file_path, "w") as f:
        f.write(json.dumps(options["batsim"]["config"], indent=4))
    return out_config_file_path


def prepare_batsim_cl(options, verbose):
    if "batsim" not in options:
        print("batsim section is missing in experiment settings", file=sys.stderr)
        sys.exit(1)

    batsim_cl = [
        get_value(
            options, [
                "batsim", "executable", "path"], [
                "batsim", "bin"], default="batsim")]
    batsim_cl += get_value(options, ["batsim",
                                     "executable", "args"], default=[])

    delete_key(options, ["batsim", "executable"])
    delete_key(options, ["batsim", "bin"])

    batsim_cl.append(
        '--export=' +
        os.path.join(
            options["output-dir"],
            options.get("export", "out")))

    if "workload-script" in options["batsim"]:
        options["batsim"]["workload"] = run_workload_script(options, verbose)
        delete_key(options, ["batsim", "workload-script"])

    if "config" in options["batsim"]:
        options["batsim"]["config-file"] = generate_config(options)
        delete_key(options, ["batsim", "config"])

    for key, val in options.get("batsim", {}).items():
        if not key.startswith("_"):
            if isinstance(val, bool):
                if not val:
                    continue
                val = ""
            else:
                val = "=" + str(val)
            batsim_cl.append("--" + key + val)

    return batsim_cl


def prepare_scheduler_cl(options, verbose):
    if "scheduler" not in options:
        print(
            "scheduler section is missing in experiment settings",
            file=sys.stderr)
        sys.exit(1)

    sched_cl = []
    if 'interpreter' in options["scheduler"]:
        if options["scheduler"]["interpreter"] == "coverage":
            interpreter = ["python3", "-m", "coverage", "run", "-a"]
        elif options["scheduler"]["interpreter"] == "pypy":
            interpreter = ["pypy", "-OOO"]
        elif options["scheduler"]["interpreter"] == "profile":
            interpreter = ["python3", "-m", "cProfile", "-o", "simul.cprof"]
        else:
            assert False, "Unknown interpreter"
        sched_cl += interpreter
        launcher_path = "launcher.py"
        if 'srcdir' in options["scheduler"]:
            launcher_path = os.path.join(
                options["scheduler"].get(
                    "srcdir", "."), launcher_path)
        sched_cl.append(launcher_path)
    else:
        sched_cl.append("pybatsim")

    sched_cl.append(options["scheduler"]["name"])

    try:
        sched_options = options["scheduler"]["options"]
    except KeyError:
        sched_options = {}
    sched_options["export-prefix"] = os.path.join(
        options["output-dir"], options.get("export", "out"))

    sched_cl.append("-o")
    sched_cl.append(json.dumps(sched_options))

    if options["scheduler"].get("verbose", False):
        sched_cl.append('-v')

    if "socket-endpoint" in options["scheduler"]:
        sched_cl.append('-s')
        sched_cl.append(options["scheduler"]["socket-endpoint"])

    if "event-socket-endpoint" in options["scheduler"]:
        sched_cl.append('-e')
        sched_cl.append(options["scheduler"]["event-socket-endpoint"])

    if "timeout" in options["scheduler"]:
        sched_cl.append('-t')
        sched_cl.append(options["scheduler"]["timeout"])

    return sched_cl


def prepare_exec_cl(options, name):
    path = options[name].get("path")
    args = options[name].get("args", [])

    if path:
        return [path] + args


def launch_experiment(options, verbose=True):
    if options.get("output-dir", "SELF") == "SELF":
        options["output-dir"] = os.path.dirname("./" + options["options-file"])
    if not os.path.exists(options["output-dir"]):
        os.makedirs(options["output-dir"])

    batsim_cl = prepare_batsim_cl(options, verbose)
    sched_cl = prepare_scheduler_cl(options, verbose)

    if "pre" in options:
        pre_cl = prepare_exec_cl(options, "pre")
        if verbose:
            print()
        pre_exec = execute_cl("pre", pre_cl, verbose=verbose)
        pre_exec.wait()
        if pre_exec.returncode != 0:
            sys.exit(pre_exec.returncode)

    with open(os.path.join(options["output-dir"], "batsim.stdout"), "w") as batsim_stdout_file, \
            open(os.path.join(options["output-dir"], "batsim.stderr"), "w") as batsim_stderr_file, \
            open(os.path.join(options["output-dir"], "sched.stdout"), "w") as sched_stdout_file, \
            open(os.path.join(options["output-dir"], "sched.stderr"), "w") as sched_stderr_file:
        if verbose:
            print()
        batsim_exec = execute_cl(
            batsim_cl[0],
            batsim_cl,
            stdout=batsim_stdout_file,
            stderr=batsim_stderr_file,
            verbose=verbose)

        if verbose:
            print()
        sched_exec = execute_cl(
            sched_cl[0],
            sched_cl,
            stdout=sched_stdout_file,
            stderr=sched_stderr_file,
            on_failure=functools.partial(
                terminate_cl,
                batsim_exec,
                terminate=True),
            verbose=verbose)

        event_socket_connect = options.get(
            "event-socket-connect", "tcp://localhost:28001")
        network_client = NetworkHandler(
            socket_endpoint=event_socket_connect, timeout=100)
        network_client.subscribe()

        try:
            if verbose:
                print("\nSimulation is in progress:")

            while True:
                if batsim_exec.poll() is not None:
                    if verbose:
                        print()
                    break
                elif sched_exec.poll() is not None:
                    if verbose:
                        print()
                    break
                time.sleep(0.5)
                if verbose:
                    while True:
                        status = network_client.recv_string()
                        if status is None:
                            break
                        rows, columns = get_terminal_size()
                        if columns:
                            if len(status) > columns:
                                status = status[:columns - 3] + "..."
                            status = status.ljust(columns)
                        print(status, end='\r', flush=True)
        except KeyboardInterrupt:
            print("\nSimulation was aborted => Terminating batsim and the scheduler")
            terminate_cl(batsim_exec)
            terminate_cl(sched_exec)

        if sched_exec.poll() is not None and sched_exec.returncode != 0 and batsim_exec.poll() is None:
            print("Scheduler has died => Terminating batsim")
            terminate_cl(batsim_exec)

        if batsim_exec.poll() is not None and batsim_exec.returncode != 0 and sched_exec.poll() is None:
            print("Batsim has died => Terminating the scheduler")
            terminate_cl(sched_exec)

        sched_exec.wait()
        batsim_exec.wait()

        ret_code = abs(batsim_exec.returncode) + abs(sched_exec.returncode)

        if verbose or ret_code != 0:
            print()
            check_print(
                "Excerpt of log: " +
                batsim_stdout_file.name,
                tail(
                    batsim_stdout_file.name,
                    5))
            check_print(
                "Excerpt of log: " +
                batsim_stderr_file.name,
                tail(
                    batsim_stderr_file.name,
                    5))
            check_print(
                "Excerpt of log: " +
                sched_stdout_file.name,
                tail(
                    sched_stdout_file.name,
                    5))
            check_print(
                "Excerpt of log: " +
                sched_stderr_file.name,
                tail(
                    sched_stderr_file.name,
                    5))

            print("Scheduler return code: " + str(sched_exec.returncode))
            print("Batsim return code: " + str(batsim_exec.returncode))

        if ret_code == 0:
            if "post" in options:
                post_cl = prepare_exec_cl(options, "post")
                if verbose:
                    print()
                post_exec = execute_cl("post", post_cl, verbose=verbose)
                post_exec.wait()
                if post_exec.returncode != 0:
                    sys.exit(post_exec.returncode)

    return ret_code
