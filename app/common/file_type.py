from enum import Enum


class FileType(str, Enum):
  PDF = "PDF"
  JPEG = "JPEG"
  JPG = "JPG"
  PNG = "PNG"
  TXT = "TXT"
