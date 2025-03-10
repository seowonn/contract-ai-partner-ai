from dataclasses import dataclass
from flask import jsonify


@dataclass
class ErrorResponse:
  code: str
  message: str

  def of(self):
    return jsonify({
      "code": self.code,
      "message": self.message
    })
