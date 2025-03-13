from dataclasses import dataclass
from typing import Optional, Any

from flask import jsonify

from app.schemas.success_code import SuccessCode


@dataclass
class SuccessResponse:
  success: SuccessCode
  data: Optional[Any] = None


  def of(self):
    return jsonify({
      "code": self.success.code,
      "message": self.success.message,
      "data": self.data
    })
