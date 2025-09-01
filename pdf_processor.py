import logging
import pdfplumber
import pytesseract
from PIL import Image
import io
import re

# Disable debug logging for PDF libraries
logging.getLogger('pdfminer').setLevel(logging.WARNING)
logging.getLogger('pdfplumber').setLevel(logging.WARNING)

def clean_text_for_api(text):
    """
    Clean text to ensure it's ASCII-safe for API transmission
    """
    if not text:
        return ""
    
    # Replace common Unicode characters with ASCII equivalents
    replacements = {
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...',  # Ellipsis
        '\u00b0': ' degrees',  # Degree symbol
        '\u00bd': '1/2',  # Half
        '\u00bc': '1/4',  # Quarter
        '\u00be': '3/4',  # Three quarters
        '\u00b2': '^2',  # Superscript 2
        '\u00b3': '^3',  # Superscript 3
        '\u2022': '*',  # Bullet
        '\u00d7': 'x',  # Multiplication
        '\u00f7': '/',  # Division
        '\u03bc': 'u',  # Micro/mu
        '\u00b1': '+/-',  # Plus-minus
        '\u2265': '>=',  # Greater than or equal
        '\u2264': '<=',  # Less than or equal
        '\u2260': '!=',  # Not equal
        '\u00a9': '(c)',  # Copyright
        '\u00ae': '(R)',  # Registered
        '\u2122': '(TM)',  # Trademark
    }
    
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-ASCII characters
    text = ''.join(char if ord(char) < 128 else ' ' for char in text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    return text.strip()

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using a multi-step approach:
    1. Try digital text extraction first (for text-based PDFs)
    2. Use OCR for pages where text extraction fails (for scanned PDFs)
    3. Extract and structure tables separately
    4. Maintain document structure and layout
    """
    
    extracted_content = []
    
    logging.info(f"Starting PDF processing for: {pdf_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logging.info(f"Processing {total_pages} pages...")
            
            for page_num, page in enumerate(pdf.pages, 1):
                page_content = []
                page_content.append(f"\n{'='*50}")
                page_content.append(f"PAGE {page_num}")
                page_content.append(f"{'='*50}\n")
                
                # Step 1: Try to extract digital text
                try:
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("Text extraction timed out")
                    
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(15)  # 15 second timeout
                    
                    try:
                        # Extract text with layout preservation
                        text = page.extract_text(layout=True, x_tolerance=2)
                        signal.alarm(0)
                    except:
                        signal.alarm(0)
                        # Fallback to simple extraction
                        text = page.extract_text()
                    
                    if text and len(text.strip()) > 50:
                        logging.info(f"Page {page_num}: Digital text extraction successful")
                        page_content.append("==DIGITAL TEXT EXTRACTION==")
                        page_content.append(clean_text_for_api(text))
                        
                        # Also try to extract tables if present
                        try:
                            tables = page.extract_tables()
                            if tables:
                                page_content.append("\n==TABLES FOUND==")
                                for idx, table in enumerate(tables, 1):
                                    if table and len(table) > 0:
                                        page_content.append(f"\nTable {idx}:")
                                        for row in table:
                                            if row:
                                                cleaned_row = []
                                                for cell in row:
                                                    cleaned_row.append(clean_text_for_api(str(cell) if cell else ""))
                                                page_content.append(" | ".join(cleaned_row))
                        except Exception as e:
                            logging.warning(f"Table extraction failed for page {page_num}: {str(e)}")
                    
                    else:
                        # Text extraction failed or returned too little, use OCR
                        raise ValueError("Insufficient text extracted")
                        
                except (TimeoutError, ValueError, Exception) as e:
                    # Step 2: Fall back to OCR
                    logging.info(f"Page {page_num}: Falling back to OCR extraction")
                    page_content.append(f"==START OF OCR FOR PAGE {page_num}==")
                    
                    try:
                        # Convert page to image for OCR
                        pil_image = page.to_image(resolution=200)
                        img = pil_image.original
                        
                        # Perform OCR with timeout protection
                        import signal
                        
                        def timeout_handler(signum, frame):
                            raise TimeoutError("OCR timed out")
                        
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(30)  # 30 second timeout for OCR
                        
                        try:
                            # Use Tesseract with page segmentation mode for better results
                            custom_config = r'--oem 3 --psm 6'
                            ocr_text = pytesseract.image_to_string(img, lang='eng', config=custom_config)
                            page_content.append(clean_text_for_api(ocr_text))
                        finally:
                            signal.alarm(0)
                            
                    except TimeoutError:
                        logging.warning(f"OCR timed out for page {page_num}")
                        page_content.append("[OCR TIMED OUT FOR THIS PAGE]")
                    except Exception as ocr_error:
                        logging.error(f"OCR failed for page {page_num}: {str(ocr_error)}")
                        page_content.append(f"[OCR FAILED: {str(ocr_error)}]")
                    
                    page_content.append(f"==END OF OCR FOR PAGE {page_num}==")
                
                extracted_content.append('\n'.join(page_content))
                
        # Combine all content
        final_content = []
        
        # Add document structure header
        final_content.append("="*60)
        final_content.append("DOCUMENT CONTENT EXTRACTION")
        final_content.append("="*60)
        
        # Add main content
        final_content.extend(extracted_content)
        
        # Final cleanup
        result = '\n'.join(final_content)
        result = clean_text_for_api(result)
        
        # Ensure the result is not too long for the API
        max_chars = 50000  # Reasonable limit
        if len(result) > max_chars:
            logging.warning(f"Content truncated from {len(result)} to {max_chars} characters")
            result = result[:max_chars] + "\n\n[CONTENT TRUNCATED DUE TO LENGTH]"
        
        logging.info(f"PDF processing complete. Extracted {len(result)} characters.")
        return result
        
    except Exception as e:
        logging.error(f"Critical error in PDF processing: {str(e)}")
        # Return whatever we managed to extract
        if extracted_content:
            return clean_text_for_api('\n'.join(extracted_content))
        else:
            return f"[PDF EXTRACTION FAILED: {str(e)}]"