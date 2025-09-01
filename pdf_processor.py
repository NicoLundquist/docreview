import logging
import pdfplumber
import pytesseract
from PIL import Image
import io
import re
import unicodedata
import platform
import threading
import signal
import string

# Disable debug logging for PDF libraries
logging.getLogger('pdfminer').setLevel(logging.WARNING)
logging.getLogger('pdfplumber').setLevel(logging.WARNING)

def clean_text_for_api(text):
    """
    Enhanced cleaning with comprehensive Unicode replacement
    """
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # First normalize Unicode to decomposed form
    try:
        text = unicodedata.normalize('NFKD', text)
    except Exception:
        pass
    
    # Comprehensive Unicode replacements - covers PDF common characters
    replacements = {
        # Quotes and punctuation
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...',  # Ellipsis
        
        # Mathematical and scientific
        '\u00b0': ' degrees',  # Degree symbol
        '\u00bd': '1/2',  # Half
        '\u00bc': '1/4',  # Quarter
        '\u00be': '3/4',  # Three quarters
        '\u00b2': '^2',  # Superscript 2
        '\u00b3': '^3',  # Superscript 3
        '\u2022': '*',  # Bullet
        '\u00d7': 'x',  # Multiplication
        '\u00f7': '/',  # Division
        '\u03bc': 'micro',  # Micro/mu
        '\u00b1': '+/-',  # Plus-minus
        '\u2265': '>=',  # Greater than or equal
        '\u2264': '<=',  # Less than or equal
        '\u2260': '!=',  # Not equal
        '\u2248': '~=',  # Approximately equal
        '\u221a': 'sqrt',  # Square root
        '\u221e': 'infinity',  # Infinity
        '\u03c0': 'pi',  # Pi
        '\u03b1': 'alpha',  # Alpha
        '\u03b2': 'beta',  # Beta
        '\u03b3': 'gamma',  # Gamma
        '\u03b4': 'delta',  # Delta
        '\u03a9': 'Omega',  # Omega
        
        # Symbols and marks
        '\u00a9': '(c)',  # Copyright
        '\u00ae': '(R)',  # Registered
        '\u2122': '(TM)',  # Trademark
        '\u00a7': 'Section ',  # Section sign
        '\u2020': '+',  # Dagger
        '\u2021': '++',  # Double dagger
        '\u00b6': '[P]',  # Pilcrow (paragraph sign)
        '\u2030': ' per thousand',  # Per mille
        '\u00ba': ' degrees',  # Masculine ordinal
        '\u00aa': 'a',  # Feminine ordinal
        '\u2032': "'",  # Prime
        '\u2033': '"',  # Double prime
        '\u2034': "'''",  # Triple prime
        '\u00b5': 'micro',  # Micro sign
        
        # Whitespace and separators
        '\u00a0': ' ',  # Non-breaking space
        '\ufeff': '',  # Zero width no-break space (BOM)
        '\u200b': '',  # Zero width space
        '\u200c': '',  # Zero width non-joiner
        '\u200d': '',  # Zero width joiner
        '\u2028': '\n',  # Line separator
        '\u2029': '\n\n',  # Paragraph separator
        '\t': ' ',  # Tab
        '\r': '',  # Carriage return
    }
    
    # Apply replacements
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remove box-drawing characters that layout=True might add
    box_chars = '│├─└┘┌┐┤┬┴┼╭╮╯╰╱╲╳┇┆┊┋'
    for char in box_chars:
        text = text.replace(char, '')
    
    # More aggressive cleaning - keep only printable ASCII characters plus newlines and tabs
    printable = set(string.printable)
    text = ''.join(char if char in printable else ' ' for char in text)
    
    # Remove control characters except \n, \r, \t
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Final safety net - ensure pure ASCII
    text = text.encode('ascii', errors='ignore').decode('ascii')
    
    # Clean up whitespace
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Trim line starts/ends
    
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
                
                # Step 1: Try to extract digital text with cross-platform timeout
                try:
                    text = None
                    
                    # Cross-platform timeout handling
                    if platform.system() != 'Windows':
                        # Unix-like systems - use signal
                        try:
                            def timeout_handler(signum, frame):
                                raise TimeoutError("Text extraction timed out")
                            
                            signal.signal(signal.SIGALRM, timeout_handler)
                            signal.alarm(15)  # 15 second timeout
                            
                            # Use layout=False to avoid Unicode box-drawing characters
                            text = page.extract_text(layout=False)
                            signal.alarm(0)
                        except TimeoutError:
                            signal.alarm(0)
                            logging.warning(f"Page {page_num}: Text extraction timed out")
                            text = None
                    else:
                        # Windows or fallback - use threading
                        try:
                            text = extract_with_timeout(page.extract_text, 15, layout=False)
                        except TimeoutError:
                            logging.warning(f"Page {page_num}: Text extraction timed out")
                            text = None
                    
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
                        
                        # Perform OCR with cross-platform timeout protection
                        ocr_text = None
                        
                        if platform.system() != 'Windows':
                            # Unix-like systems - use signal
                            try:
                                def timeout_handler(signum, frame):
                                    raise TimeoutError("OCR timed out")
                                
                                signal.signal(signal.SIGALRM, timeout_handler)
                                signal.alarm(30)  # 30 second timeout for OCR
                                
                                # OCR with better configuration for text preservation
                                custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=0'
                                ocr_text = pytesseract.image_to_string(img, lang='eng', config=custom_config)
                                signal.alarm(0)
                                
                            except TimeoutError:
                                signal.alarm(0)
                                logging.warning(f"OCR timed out for page {page_num}")
                                ocr_text = None
                        else:
                            # Windows or fallback - use threading
                            try:
                                def perform_ocr():
                                    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=0'
                                    return pytesseract.image_to_string(img, lang='eng', config=custom_config)
                                
                                ocr_text = extract_with_timeout(perform_ocr, 30)
                            except TimeoutError:
                                logging.warning(f"OCR timed out for page {page_num}")
                                ocr_text = None
                        
                        # Clean OCR text immediately and aggressively
                        if ocr_text:
                            # Clean immediately to avoid Unicode propagation
                            ocr_text = clean_text_for_api(ocr_text)
                            # Additional OCR-specific cleaning
                            ocr_text = re.sub(r'[^\x20-\x7E\n\r\t]', '', ocr_text)  # Keep only printable ASCII
                            if ocr_text.strip():
                                page_content.append(ocr_text)
                            else:
                                page_content.append("[OCR PRODUCED NO READABLE TEXT]")
                        else:
                            page_content.append("[OCR TIMED OUT FOR THIS PAGE]")
                            
                    except Exception as ocr_error:
                        # Clean error messages too!
                        error_msg = str(ocr_error)
                        error_msg = error_msg.encode('ascii', errors='ignore').decode('ascii')
                        logging.error(f"OCR failed for page {page_num}: {error_msg}")
                        page_content.append(f"[OCR FAILED: {error_msg}]")
                    
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
        
        # No truncation - send full content to API
        logging.info(f"Full content extracted: {len(result)} characters")
        
        logging.info(f"PDF processing complete. Extracted {len(result)} characters.")
        return result
        
    except Exception as e:
        logging.error(f"Critical error in PDF processing: {str(e)}")
        # Return whatever we managed to extract
        if extracted_content:
            return clean_text_for_api('\n'.join(extracted_content))
        else:
            return f"[PDF EXTRACTION FAILED: {str(e)}]"