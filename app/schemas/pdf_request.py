from dataclasses import dataclass


@dataclass
class PDFRequest:
  s3_path: str
  category: str
  reference_id: int