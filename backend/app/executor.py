import subprocess
import sys
import os
import json
import tempfile

EXECUTION_TIMEOUT_SECONDS = 60.0

def run_in_sandbox(code: str) -> dict:
    # Set PYTHONPATH so the worker can load the local 'app' package.
    # Do not add backend/app here; it would shadow the installed 'sia' package.
    env = os.environ.copy()
    app_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env["PYTHONPATH"] = app_parent_dir + os.path.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    quantum_output = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl")
    quantum_output_path = quantum_output.name
    quantum_output.close()
    env["SIA_QUANTUM_OUTPUT_PATH"] = quantum_output_path
    
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "app.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=app_parent_dir
        )
        
        try:
            stdout, stderr = proc.communicate(input=code, timeout=EXECUTION_TIMEOUT_SECONDS)
            success = proc.returncode == 0
            
            error_msg = None
            if not success:
                if "[Error: Output limit of 1 MB exceeded]" in stdout or "[Error: Output limit of 1 MB exceeded]" in stderr:
                    error_msg = "Output limit of 1 MB exceeded"
                else:
                    error_msg = "Runtime error during execution"
            
            return {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "error": error_msg,
                "quantum_results": _read_quantum_results(quantum_output_path)
            }
            
        except subprocess.TimeoutExpired:
            proc.kill()
            # Retrieve remaining output streams after killing
            stdout, stderr = proc.communicate()
            return {
                "success": False,
                "stdout": stdout,
                "stderr": stderr,
                "error": f"Runtime timeout: Execution exceeded {int(EXECUTION_TIMEOUT_SECONDS)} seconds limit",
                "quantum_results": _read_quantum_results(quantum_output_path)
            }
            
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Failed to spawn sandbox worker: {str(e)}",
            "error": "Internal execution error",
            "quantum_results": _read_quantum_results(quantum_output_path)
        }
    finally:
        try:
            os.remove(quantum_output_path)
        except OSError:
            pass


def _read_quantum_results(path: str) -> list:
    results = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return results
    return results
