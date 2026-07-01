from pydantic import BaseModel
from typing import Any, Optional

class RunRequest(BaseModel):
    code: str

class RunResponse(BaseModel):
    success: bool
    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    error: Optional[str] = None
    quantum_results: Optional[list[dict[str, Any]]] = None
