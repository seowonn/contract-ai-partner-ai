from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.schemas.analysis_response import RagResult


class ChunkProcessStatus(Enum):
  SUCCESS = "success"
  FAILURE = "failure"

@dataclass
class ChunkProcessResult:
  status: ChunkProcessStatus
  result: Optional[RagResult] = None