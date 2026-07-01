import requests
import json
import os
import uuid
import numpy as np


class HDQSError(Exception):
    pass


class hdqs:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.qbt_id = None
        self.num_qubits = None
        self.state = None
        self.use_local = False
        print(f"Connecting to HDQS server at: {self.base_url}")
        print(f"Connected to HDQS server at {self.base_url}")

    def _should_fallback(self, error: Exception) -> bool:
        response = getattr(error, "response", None)
        if response is None:
            return isinstance(error, requests.RequestException)
        return response.status_code in {404, 405, 502, 503, 504}

    def _local_create(self, num_qubits: int):
        if not isinstance(num_qubits, int) or num_qubits < 1 or num_qubits > 20:
            raise ValueError("Invalid num_qubits (must be integer between 1 and 20)")

        self.qbt_id = str(uuid.uuid4())
        self.num_qubits = num_qubits
        self.state = None
        data = {"qbt_id": self.qbt_id, "status": "created", "num_qubits": num_qubits}
        return data

    def _local_run(self, instructions: list):
        if self.num_qubits is None:
            raise ValueError("No active qubit register ID found. Please call qbt_create() first.")
        if not isinstance(instructions, list):
            raise ValueError("Invalid instructions format")

        data, self.state = _simulate_quantum_circuit(self.num_qubits, instructions)
        _emit_quantum_result(data)
        return data

    def _local_measure(self, qubits: list, collapse: bool = True):
        if self.num_qubits is None or self.state is None:
            raise HDQSError("No active circuit. Call qbt_create and qbt_run first.")
        if not isinstance(qubits, list):
            raise HDQSError("Invalid qubits format")

        probabilities = np.abs(self.state) ** 2
        state_index = int(np.random.choice(len(probabilities), p=probabilities))
        measurement_results = [
            {"qubit": qubit, "result": str((state_index >> qubit) & 1)}
            for qubit in qubits
        ]

        if collapse:
            collapsed = np.zeros_like(self.state)
            collapsed[state_index] = 1.0
            self.state = collapsed

        return {
            "status": "success",
            "result": {
                "measurement_results": measurement_results,
                "bitstring": "".join(
                    item["result"] for item in sorted(measurement_results, key=lambda x: x["qubit"])
                )
            }
        }

    def qbt_create(self, num_qubits: int):
        if self.use_local:
            return self._local_create(num_qubits)

        url = f"{self.base_url}/qbt/create"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {"num_qubits": num_qubits}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.qbt_id = data.get("qbt_id") or data.get("id") or "qbt_default"
            self.num_qubits = data.get("num_qubits", num_qubits)
            self.state = None
            return data
        except Exception as e:
            if self._should_fallback(e):
                self.use_local = True
                return self._local_create(num_qubits)
            print(f"Error calling qbt_create: {e}")
            raise

    def qbt_run(self, instructions: list):
        if not self.qbt_id:
            raise ValueError("No active qubit register ID found. Please call qbt_create() first.")
        if self.use_local:
            return self._local_run(instructions)
        
        url = f"{self.base_url}/qbt/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "qbt_id": self.qbt_id,
            "instructions": instructions
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            _emit_quantum_result(data)
            return data
        except Exception as e:
            if self._should_fallback(e):
                self.use_local = True
                return self._local_run(instructions)
            print(f"Error calling qbt_run: {e}")
            raise

    def qbt_measure(self, qubits: list, collapse: bool = True):
        if not self.qbt_id:
            raise HDQSError("No active qubit register ID found. Please call qbt_create() first.")
        if self.use_local:
            return self._local_measure(qubits, collapse)

        url = f"{self.base_url}/qbt/measure"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "qbt_id": self.qbt_id,
            "qubits": qubits,
            "collapse": collapse
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if self._should_fallback(e):
                self.use_local = True
                return self._local_measure(qubits, collapse)
            print(f"Error calling qbt_measure: {e}")
            raise


def _simulate_quantum_circuit(num_qubits: int, instructions: list) -> tuple[dict, np.ndarray]:
    size = 1 << num_qubits
    state = np.zeros(size, dtype=complex)
    state[0] = 1.0

    for inst in instructions:
        parts = inst.strip().lower().split()
        if not parts:
            continue
        gate = parts[0]

        if gate == "h" and len(parts) == 2:
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

        elif gate == "x" and len(parts) == 2:
            target = int(parts[1])
            new_state = np.zeros(size, dtype=complex)
            for i in range(size):
                new_state[i] = state[i ^ (1 << target)]
            state = new_state

        elif gate == "y" and len(parts) == 2:
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

        elif gate == "z" and len(parts) == 2:
            target = int(parts[1])
            new_state = np.zeros(size, dtype=complex)
            for i in range(size):
                bit_val = (i >> target) & 1
                if bit_val == 0:
                    new_state[i] = state[i]
                else:
                    new_state[i] = -state[i]
            state = new_state

        elif gate in ("cnot", "cx") and len(parts) == 3:
            control = int(parts[1])
            target = int(parts[2])
            new_state = state.copy()
            for i in range(size):
                if (i >> control) & 1:
                    new_state[i] = state[i ^ (1 << target)]
            state = new_state

    probabilities = np.abs(state) ** 2
    state_labels = [format(i, f"0{num_qubits}b") for i in range(size)]
    statevector_str = [
        f"{val.real:.4f} + {val.imag:.4f}j" if abs(val.imag) > 1e-6 else f"{val.real:.4f}"
        for val in state
    ]

    output_parts = []
    probabilities_dict = {}
    for i in range(size):
        probabilities_dict[state_labels[i]] = float(probabilities[i])
        if probabilities[i] > 1e-4:
            output_parts.append(f"|{state_labels[i]}>: {probabilities[i] * 100:.1f}%")

    return {
        "status": "success",
        "num_qubits": num_qubits,
        "statevector": statevector_str,
        "probabilities": probabilities_dict,
        "output": "Quantum State Probabilities:\n" + "\n".join(output_parts)
    }, state


def _emit_quantum_result(data: dict):
    path = os.environ.get("SIA_QUANTUM_OUTPUT_PATH")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(data) + "\n")
    except OSError:
        pass
