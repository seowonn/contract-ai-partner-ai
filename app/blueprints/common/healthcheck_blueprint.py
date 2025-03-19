from flask import Blueprint, jsonify

health = Blueprint('health', __name__, url_prefix="/health-check")

@health.route('/', methods=['GET'])
def health_check():
  return jsonify({"status": "healthy"}), 200