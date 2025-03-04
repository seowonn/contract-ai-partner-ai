from flask import Blueprint, request, jsonify, send_file

bp = Blueprint('reference_document', __name__, url_prefix="/reference-document")

@bp.route('', methods=['POST'])
def process_pdf_from_s3():
