from dataclasses import dataclass, field
from typing import List


def to_camel_case(snake_str: str) -> str:
  components = snake_str.split('_')
  return components[0] + ''.join(x.title() for x in components[1:])

@dataclass
class RagResult:
  clause_content: str
  proof_texts: List[str] = field(default_factory=list)
  incorrect_texts: List[str] = field(default_factory=list)
  corrected_texts: List[str] = field(default_factory=list)

@dataclass
class AnalysisResponse:
  summary_content: str
  total_page: int
  chunks: List[RagResult]

