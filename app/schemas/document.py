from dataclasses import dataclass


@dataclass
class DocumentMetadata:
  page: int

@dataclass
class Document:
  page_content: str
  metadata: DocumentMetadata


