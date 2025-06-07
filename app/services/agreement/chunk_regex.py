CHUNKING_REGEX = [
  {
    "name": "ARTICLE_CHUNK_PATTERN",
    "regex": r"(제\s*\d+\s*조\s*(?:【[^】\n]*】?|[^】\n]*】|\([^)\\n]*\)?|\[[^\]\n]*\]?))\s*(.*?)(?=(?:제\s*\d+\s*조\s*(?:【[^】\n]*】?|[^】\n]*】|\([^)\\n]*\)?|\[[^\]\n]*\]?|)|$))"
  },
  {
    "name": "NUMBER_HEADER_PATTERN",
    "regex": r"(?:^|\n)(\d+\.\s.*?)(?=\n\d+\.|\Z)"
  }
]
