"""OCR utilities (stub first, extend later)."""
from datetime import date
from decimal import Decimal

def extract_fields(path: str):
    # TODO: Implement real OCR with pytesseract + OpenCV
    # For now we return a stub so the pipeline works end-to-end.
    return {
        "merchant": "STUB MERCHANT",
        "amount": Decimal("0.00"),
        "date": date.today(),
        "raw": "(ocr not yet implemented)"
    }
