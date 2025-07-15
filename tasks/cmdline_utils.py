import subprocess


def run_bash_cmd(cmd, raise_on_error=True, log_cmd=False):
    """Run a command in the terminal and return the output.

    Dangerous to log the cmd in case it contains tokens. Should probably remove this altogether.
    """
    if log_cmd:
        # TODO: using logging pkg
        print(cmd)
    result = subprocess.run(cmd, shell=True, text=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    if raise_on_error and result.returncode != 0:
        raise Exception(f"Command failed with return code {result.returncode}: {result.stdout.strip()}")

    return result.stdout.strip(), result.returncode
