import re
from dataclasses import dataclass
from typing import List


@dataclass
class ClauseChunk:
  clause_number: str
  content: str


@dataclass
class ArticleChunk:
  article_number: str
  clauses: List[ClauseChunk]


def split_text_by_pattern(text: str, pattern: str) -> List[str]:
  return re.split(pattern, text)


def chunk_by_article_and_clause(extracted_text: str) -> List[ArticleChunk]:
  """
  1. 조(Article)를 찾으면 즉시 해당 조에서 항(Paragraph)까지 세부 분리하여 저장.
  2. '제N조'가 반드시 줄 바꿈 후 등장하고, 뒤에는 공백과 특정 기호만 허용 (문자X).
  3. 각 조 내부에서 '①, ②, ③' 또는 '1., 2.' 등의 패턴을 찾아 항을 분리.
  """
  article_pattern = r'\n(제\s*\d+조[\s\(\.\[\]<>]*)'  # 조(Article) 기준 정규식
  clause_pattern = r'(\n\s*\d+항|\n\s*[①-⑨]|\n\s*\d+\.)'  # 항(Paragraph) 기준 정규식

  chunks = split_text_by_pattern(extracted_text, article_pattern)
  result: List[ArticleChunk] = []

  for i in range(1, len(chunks), 2):
    article_title = chunks[i].strip()
    article_body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""

    # ✅ 조를 찾은 즉시 항을 분리
    clauses = []
    clause_chunks = split_text_by_pattern(article_body, clause_pattern)

    for j in range(1, len(clause_chunks), 2):
      clause_title = clause_chunks[j].strip()
      clause_body = clause_chunks[j + 1].strip() if j + 1 < len(
        clause_chunks) else ""
      clauses.append(
          ClauseChunk(clause_number=clause_title, content=clause_body))

    result.append(ArticleChunk(article_number=article_title, clauses=clauses))

  return result  # ✅ 조 + 항 구조 유지한 채 반환
