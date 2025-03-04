import pypdf

def extract_text_from_pdf(pdf_bytes_io):
    reader = pypdf.PdfReader(pdf_bytes_io)
    extracted_text = ""

    for page in reader.pages:
        extracted_text += page.extract_text() + "\n"

    return extracted_text.strip()