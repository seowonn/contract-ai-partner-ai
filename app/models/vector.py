from dataclasses import dataclass, asdict


@dataclass
class VectorPayload:
  standard_id: int
  category: str
  incorrect_text: str
  proof_text: str
  corrected_text: str
  created_at: str

  def to_dict(self):
    return asdict(self)

