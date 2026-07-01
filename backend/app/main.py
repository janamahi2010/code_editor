import os
import uuid
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models import RunRequest, RunResponse
from app.validator import validate_code
from app.executor import run_in_sandbox

app = FastAPI(title="QuantumSIA Platform API")

# Configure CORS for local development and split hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database of created quantum registers
quantum_registers = {}

def simulate_quantum_circuit(num_qubits: int, instructions: list) -> dict:
    size = 1 << num_qubits
    state = np.zeros(size, dtype=complex)
    state[0] = 1.0  # Initialize to state |00...0>

    for inst in instructions:
        parts = inst.strip().lower().split()
        if not parts:
            continue
        gate = parts[0]
        
        if gate == 'h' and len(parts) == 2:
            target = int(parts[1])
            new_state = np.zeros(size, dtype=complex)
            for i in range(size):
                bit_val = (i >> target) & 1
                i0 = i & ~(1 << target)
                i1 = i | (1 << target)
                if bit_val == 0:
                    new_state[i] = (state[i0] + state[i1]) / np.sqrt(2)
                else:
                    new_state[i] = (state[i0] - state[i1]) / np.sqrt(2)
            state = new_state
            
        elif gate == 'x' and len(parts) == 2:
            target = int(parts[1])
            new_state = np.zeros(size, dtype=complex)
            for i in range(size):
                new_state[i] = state[i ^ (1 << target)]
            state = new_state
            
        elif gate == 'y' and len(parts) == 2:
            target = int(parts[1])
            new_state = np.zeros(size, dtype=complex)
            for i in range(size):
                bit_val = (i >> target) & 1
                opp_idx = i ^ (1 << target)
                if bit_val == 0:
                    new_state[i] = 1j * state[opp_idx]
                else:
                    new_state[i] = -1j * state[opp_idx]
            state = new_state
            
        elif gate == 'z' and len(parts) == 2:
            target = int(parts[1])
            new_state = np.zeros(size, dtype=complex)
            for i in range(size):
                bit_val = (i >> target) & 1
                if bit_val == 0:
                    new_state[i] = state[i]
                else:
                    new_state[i] = -state[i]
            state = new_state
            
        elif gate in ('cnot', 'cx') and len(parts) == 3:
            control = int(parts[1])
            target = int(parts[2])
            new_state = state.copy()
            for i in range(size):
                if (i >> control) & 1:
                    new_state[i] = state[i ^ (1 << target)]
            state = new_state

    probabilities = np.abs(state) ** 2
    state_labels = [format(i, f'0{num_qubits}b') for i in range(size)]
    statevector_str = [f"{val.real:.4f} + {val.imag:.4f}j" if abs(val.imag) > 1e-6 else f"{val.real:.4f}" for val in state]
    
    output_parts = []
    probabilities_dict = {}
    for i in range(size):
        probabilities_dict[state_labels[i]] = float(probabilities[i])
        if probabilities[i] > 1e-4:
            output_parts.append(f"|{state_labels[i]}>: {probabilities[i]*100:.1f}%")
            
    return {
        "status": "success",
        "num_qubits": num_qubits,
        "statevector": statevector_str,
        "probabilities": probabilities_dict,
        "output": "Quantum State Probabilities:\n" + "\n".join(output_parts)
    }

@app.post("/run", response_model=RunResponse)
async def run_code(request: RunRequest):
    try:
        # Enforce size limits and compile safety AST rules
        validate_code(request.code)
    except ValueError as ve:
        return RunResponse(
            success=False,
            stdout="",
            stderr="",
            error=str(ve)
        )
    
    # Execute user code inside sandboxed subprocess worker
    result = run_in_sandbox(request.code)
    return RunResponse(
        success=result["success"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        error=result["error"]
    )

# Mock HDQS API endpoints for local sandbox client calls
@app.post("/qbt/create")
async def qbt_create(data: dict):
    num_qubits = data.get("num_qubits")
    if not isinstance(num_qubits, int) or num_qubits < 1 or num_qubits > 20:
        raise HTTPException(status_code=400, detail="Invalid num_qubits (must be integer between 1 and 20)")
    
    qbt_id = str(uuid.uuid4())
    quantum_registers[qbt_id] = num_qubits
    return {"qbt_id": qbt_id, "status": "created", "num_qubits": num_qubits}

@app.post("/qbt/run")
async def qbt_run(data: dict):
    qbt_id = data.get("qbt_id")
    instructions = data.get("instructions")
    
    if not qbt_id or qbt_id not in quantum_registers:
        raise HTTPException(status_code=400, detail="Invalid or missing qbt_id")
    if not isinstance(instructions, list):
        raise HTTPException(status_code=400, detail="Invalid instructions format")
    
    num_qubits = quantum_registers[qbt_id]
    sim_result = simulate_quantum_circuit(num_qubits, instructions)
    return sim_result

# Serve static frontend webapp (index.html, style.css, js)
app_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.abspath(os.path.join(app_dir, "..", "..", "frontend"))

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
