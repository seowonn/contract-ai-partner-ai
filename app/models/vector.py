from dataclasses import dataclass, field
from typing import List


@dataclass
class VectorPayload:
  standard_id: int
  incorrect_text: str | None
  proof_text: str | None
  corrected_text: str | None
  created_at: str

  def to_dict(self) -> dict:
    return {
      "standard_id": self.standard_id or "",
      "incorrect_text": self.incorrect_text or "",
      "proof_text": self.proof_text or "",
      "corrected_text": self.corrected_text or "",
      "created_at": self.created_at or ""
    }

  def embedding_input(self) -> str:
    return self.proof_text

@dataclass
class WordPayload:
  standard_id: int
  original_text: str
  term: str
  created_at: str
  keywords: List[str] = field(default_factory=list)

  def to_dict(self) -> dict:
    return {
      "standard_id": self.standard_id or "",
      "original_text": self.original_text or "",
      "term": self.term or "",
      "keywords": self.keywords or [],
      "created_at": self.created_at or ""
    }

  def embedding_input(self) -> str:
    return f"{self.original_text} 관련 키워드: {' '.join(self.keywords)}"

