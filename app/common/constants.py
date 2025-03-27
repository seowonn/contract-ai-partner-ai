from enum import Enum


class Constants(str, Enum):
  QDRANT_COLLECTION = "standard"
  SUCCESS = "success"
  TEST_COLLECTION = "test"
  ARTICLE_HEADER_PATTERN = r'^\s*제\s*\d+\s*조'
  ARTICLE_BODY_PATTERN = r'(제\d+조\s*【[^】]+】)(.*?)(?=(?:제\d+조\s*【[^】]+】|$))'
  CLAUSE_TEXT_SEPARATOR = "!!!"

