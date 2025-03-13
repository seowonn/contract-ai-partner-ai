from pydantic import BaseModel


class PDFRequest(BaseModel):
  s3Path: str
  category: str
  standardId: int