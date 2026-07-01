import pypdf
import io
import logging

def parse_pdf_resume(file_bytes) -> str:
    """
    Extracts text from a PDF resume file stream.
    
    Args:
        file_bytes: Bytes of the uploaded PDF file.
        
    Returns:
        str: Extracted text contents.
    """
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        logging.error(f"Error parsing PDF resume: {e}")
        return ""
