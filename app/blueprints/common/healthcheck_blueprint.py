from flask import Blueprint, jsonify

health = Blueprint('health', __name__)

@health.route('/health-check', methods=['GET'])
def health_check():
  return jsonify({"status": "healthy"}), 200