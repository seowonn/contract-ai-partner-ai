from pydantic import BaseModel

from app.common.file_type import FileType


class PDFRequest(BaseModel):
  s3Path: str
  category: str
  standardId: int
  fileType: FileType