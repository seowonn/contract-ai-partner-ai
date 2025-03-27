from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RagResult:
  page: int
  order_index: int
  accuracy: Optional[float] = None
  corrected_text: Optional[str] = None
  incorrect_text: Optional[str] = None
  proof_text: Optional[str] = None
  position: List[int] = field(default_factory=list)

@dataclass
class AnalysisResponse:
  summary_content: str
  total_page: int
  chunks: List[RagResult]

