import logging
import pdfplumber
import pytesseract
from PIL import Image
import io

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file using pdfplumber
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        logging.info(f"Starting text extraction from PDF: {pdf_path}")
        
        extracted_text = ""
        
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logging.info(f"PDF has {total_pages} pages")
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Add page marker for reference
                    extracted_text += f"\n--- PAGE {page_num} ---\n"
                    
                    # Extract text from the page with error handling
                    page_text = ""
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text
                    except Exception as text_error:
                        logging.warning(f"Text extraction failed for page {page_num}: {str(text_error)}")
                        # Try alternative text extraction method
                        try:
                            # Fallback: try to extract text using different method
                            page_chars = page.chars
                            if page_chars:
                                page_text = ''.join([char.get('text', '') for char in page_chars])
                                if page_text:
                                    extracted_text += page_text
                        except Exception as fallback_error:
                            logging.warning(f"Fallback text extraction also failed for page {page_num}: {str(fallback_error)}")
                            extracted_text += f"\n[TEXT EXTRACTION FAILED FOR PAGE {page_num}]\n"
                        
                    # Try to extract table data if present with error handling
                    try:
                        tables = page.extract_tables()
                        if tables:
                            extracted_text += f"\n--- TABLES ON PAGE {page_num} ---\n"
                            for table_num, table in enumerate(tables, 1):
                                try:
                                    extracted_text += f"\nTable {table_num}:\n"
                                    for row in table:
                                        if row:
                                            # Filter out None values and join
                                            clean_row = [str(cell) if cell is not None else "" for cell in row]
                                            extracted_text += " | ".join(clean_row) + "\n"
                                except Exception as table_row_error:
                                    logging.warning(f"Error processing table {table_num} on page {page_num}: {str(table_row_error)}")
                                    continue
                    except Exception as table_error:
                        logging.warning(f"Table extraction failed for page {page_num}: {str(table_error)}")
                    
                    # Extract text from images using OCR (ensures we capture all information)
                    # Only run OCR if we didn't get much text from regular extraction
                    if not page_text or len(page_text.strip()) < 100:
                        try:
                            # Convert page to image for OCR processing with lower resolution for speed
                            page_img = page.to_image(resolution=150)
                            if page_img and hasattr(page_img, 'original'):
                                pil_img = page_img.original
                                
                                # Use OCR with timeout and simpler config for speed
                                import signal
                                
                                def timeout_handler(signum, frame):
                                    raise TimeoutError("OCR processing timed out")
                                
                                # Set up timeout (15 seconds max for OCR)
                                signal.signal(signal.SIGALRM, timeout_handler)
                                signal.alarm(15)
                                
                                try:
                                    # Use faster OCR config
                                    ocr_text = pytesseract.image_to_string(pil_img, config='--psm 6 --oem 3', timeout=10)
                                    if ocr_text and ocr_text.strip():
                                        extracted_text += f"\n--- OCR EXTRACTED TEXT FROM PAGE {page_num} ---\n"
                                        extracted_text += ocr_text.strip()
                                finally:
                                    signal.alarm(0)  # Cancel the alarm
                                    
                        except TimeoutError:
                            logging.warning(f"OCR processing timed out for page {page_num}")
                            if not page_text.strip():
                                extracted_text += f"\n[PAGE {page_num} CONTAINS IMAGES - OCR TIMED OUT]\n"
                        except Exception as ocr_error:
                            logging.warning(f"OCR processing failed for page {page_num}: {str(ocr_error)}")
                            if not page_text.strip():
                                extracted_text += f"\n[PAGE {page_num} MIGHT CONTAIN IMAGE-BASED TEXT - OCR FAILED]\n"
                    
                    logging.debug(f"Processed page {page_num}/{total_pages}")
                    
                except Exception as page_error:
                    logging.warning(f"Error processing page {page_num}: {str(page_error)}")
                    extracted_text += f"\n--- PAGE {page_num} (ERROR PROCESSING) ---\n"
                    continue
        
        if not extracted_text.strip():
            # Last resort: log detailed information and provide a more helpful error
            logging.error(f"No text content could be extracted from PDF: {pdf_path}")
            raise ValueError("Unable to extract readable text from this PDF. The file may be corrupted, heavily image-based, or use unsupported formatting. Please ensure the PDF contains readable text or try a different file.")
        
        logging.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
        return extracted_text.strip()
        
    except Exception as e:
        logging.error(f"PDF processing error for {pdf_path}: {str(e)}")
        raise Exception(f"Failed to process PDF: {str(e)}")

def validate_pdf_content(text: str) -> bool:
    """
    Validate that extracted PDF content appears to contain meaningful engineering data
    
    Args:
        text (str): Extracted text content
        
    Returns:
        bool: True if content appears valid
    """
    if not text or len(text.strip()) < 50:
        return False
    
    # Check for common engineering terms/patterns
    engineering_indicators = [
        'specification', 'requirements', 'pressure', 'temperature', 'capacity',
        'material', 'design', 'performance', 'dimensions', 'standards',
        'rating', 'model', 'technical', 'flow', 'power', 'efficiency'
    ]
    
    text_lower = text.lower()
    found_indicators = sum(1 for indicator in engineering_indicators if indicator in text_lower)
    
    # Require at least 3 engineering-related terms
    return found_indicators >= 3
