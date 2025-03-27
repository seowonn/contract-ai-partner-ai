from dataclasses import dataclass, field
from typing import List, Optional


def to_camel_case(snake_str: str) -> str:
  components = snake_str.split('_')
  return components[0] + ''.join(x.title() for x in components[1:])

@dataclass
class ClauseData:
  order_index: int = 0
  page: int = 0
  position: List[List[float]] = field(default_factory=list)

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
  summary_content: str = ""
  total_page: int = 0
  chunks: List[RagResult] = field(default_factory=list)

