from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClauseData:
  order_index: int = 0
  page: int = 0
  position: List[List[float]] = field(default_factory=list)

@dataclass
class RagResult:
  incorrect_text: Optional[str] = None
  corrected_text: Optional[str] = None
  proof_text: Optional[str] = None
  accuracy: Optional[float] = None
  clause_data: ClauseData = field(default_factory=ClauseData)

@dataclass
class AnalysisResponse:
  summary_content: str = ""
  total_page: int = 0
  chunks: List[RagResult] = field(default_factory=list)

