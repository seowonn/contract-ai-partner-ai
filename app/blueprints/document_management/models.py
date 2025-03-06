from dataclasses import dataclass
from typing import List


@dataclass
class PDFRequest:
  s3_path: str
  category: str
  reference_id: str

@dataclass
class ClauseChunk:
  clause_number: str
  clause_content: str


@dataclass
class ArticleChunk:
  article_number: str
  clauses: List[ClauseChunk]