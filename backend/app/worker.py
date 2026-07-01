import sys
import os
import traceback

MAX_OUTPUT_BYTES = 1024 * 1024  # 1 MB

class LimitedStream:
    def __init__(self, original_stream, limit):
        self.original_stream = original_stream
        self.limit = limit
        self.bytes_written = 0

    def write(self, data):
        if not data:
            return 0
        encoded = data.encode('utf-8') if isinstance(data, str) else data
        if self.bytes_written + len(encoded) > self.limit:
            self.original_stream.write("\n[Error: Output limit of 1 MB exceeded]\n")
            self.original_stream.flush()
            sys.exit(1)
        self.bytes_written += len(encoded)
        return self.original_stream.write(data)

    def flush(self):
        self.original_stream.flush()

    def __getattr__(self, attr):
        return getattr(self.original_stream, attr)

# Clear environment variables at startup, keeping only system-critical directories
# (essential for loading system DLLs/Winsock on Windows and core libraries on Linux)
safe_env_keys = {'systemroot', 'systemdrive', 'windir', 'path', 'temp', 'tmp', 'sia_quantum_output_path'}
for key in list(os.environ.keys()):
    if key.lower() not in safe_env_keys:
        del os.environ[key]

def run_worker():
    # Read user code from stdin
    code = sys.stdin.read()
    
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Configure stdout/stderr output limits
    sys.stdout = LimitedStream(sys.stdout, MAX_OUTPUT_BYTES)
    sys.stderr = LimitedStream(sys.stderr, MAX_OUTPUT_BYTES)
    
    # Capture the original python import function
    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __builtins__['__import__']
    
    # Custom safe import hook
    allowed_imports = {'numpy', 'requests', 'sia', 'collections', 'math'}
    
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        root_module = name.split('.')[0]
        if root_module not in allowed_imports:
            raise ImportError(f"Import not allowed: {name}")
        return original_import(name, globals, locals, fromlist, level)
    
    # Sandbox environment: Restrict standard builtins
    safe_builtins = {
        "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
        "divmod": divmod, "enumerate": enumerate, "filter": filter, "float": float,
        "format": format, "frozenset": frozenset, "hash": hash, "hex": hex,
        "id": id, "int": int, "isinstance": isinstance, "issubclass": issubclass,
        "iter": iter, "len": len, "list": list, "map": map, "max": max,
        "min": min, "next": next, "object": object, "oct": oct, "ord": ord,
        "pow": pow, "print": print, "property": property, "range": range,
        "repr": repr, "reversed": reversed, "round": round, "set": set,
        "slice": slice, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
        "type": type, "zip": zip,
        "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
        "IndexError": IndexError, "AttributeError": AttributeError, "NameError": NameError,
        "ZeroDivisionError": ZeroDivisionError, "Exception": Exception, "AssertionError": AssertionError,
        "ImportError": ImportError, "StopIteration": StopIteration, "RuntimeError": RuntimeError,
        "__import__": safe_import
    }
    
    execution_globals = {
        "__builtins__": safe_builtins,
        "__name__": "__main__"
    }
    
    try:
        # Pre-compile the code string
        code_obj = compile(code, "<student_code>", "exec")
        exec(code_obj, execution_globals)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        # Filter traceback to remove worker runner internals
        tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
        cleaned_tb = []
        for line in tb_lines:
            if "worker.py" not in line:
                cleaned_tb.append(line)
        sys.stderr.write("".join(cleaned_tb))
        sys.exit(1)

if __name__ == "__main__":
    run_worker()
