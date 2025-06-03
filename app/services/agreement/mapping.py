from typing import List, Tuple, Callable, Dict

from app.common.constants import ARTICLE_CHUNK_PATTERN, NUMBER_HEADER_PATTERN
from app.services.agreement.chunking import \
  chunk_by_article_and_clause_with_page, parse_article_header, \
  parse_number_header

CHUNKING_STRATEGIES: List[Tuple[str, Callable]] = [
    (ARTICLE_CHUNK_PATTERN, chunk_by_article_and_clause_with_page),
    (NUMBER_HEADER_PATTERN, chunk_by_article_and_clause_with_page)
]

HEADER_PARSERS: Dict[str, Callable[[str], Tuple[int, str]]] = {
    ARTICLE_CHUNK_PATTERN: parse_article_header,
    NUMBER_HEADER_PATTERN: parse_number_header
}