QDRANT_COLLECTION = "standard"
SUCCESS = "success"
TEST_COLLECTION = "test"
ARTICLE_HEADER_PATTERN = r'^\s*제\s*\d+\s*조'
ARTICLE_CHUNK_PATTERN = r'(제\d+조\s*(?:【[^】]+】|\([^)]+\)))(.*?)(?=(?:제\d+조\s*(?:【[^】]+】|\([^)]+\))|$))'
CLAUSE_TEXT_SEPARATOR = "!!!"
ARTICLE_CLAUSE_SEPARATOR = "+"

