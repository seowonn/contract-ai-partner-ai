from pydantic import BaseModel


class DocumentRequest(BaseModel):
  url: str
  categoryName: str
  id: int
