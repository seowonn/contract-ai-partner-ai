from pydantic import BaseModel

from app.common.file_type import FileType


class DocumentRequest(BaseModel):
  url: str
  categoryName: str
  id: int
  type: FileType