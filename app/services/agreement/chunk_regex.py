CHUNKING_REGEX = [
  {
    "name": "WORD_HEADER_PATTERN",
    "regex": r"(제\s*\d+\s*조(?:\s*【[^\n】]*】)?(?:.*?))(?=제\s*\d+\s*조|$)"
  },
  {
    "name": "NUMBER_HEADER_PATTERN",
    "regex": r"(?:^|\n)(\d+\.\s.*?)(?=\n\d+\.|\Z)"
  }
]

ARTICLE_NUMBER = {
  "NUMBER_HEADER_PATTERN": r"제\s*(\d+)\s*조",
  "WORD_HEADER_PATTERN": r"\b(\d+)\."
}
