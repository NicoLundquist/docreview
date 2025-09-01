import logging
import pdfplumber
import PyPDF2

def extract_text_from_pdf_simple(pdf_path: str) -> str:
    """
    Simple PDF text extraction with minimal processing to avoid memory issues
    """
    import pdfplumber
    
    extracted_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Simple text extraction without complex layout analysis
                    page_text = page.extract_text(layout=False, x_tolerance=2, y_tolerance=2)
                    if page_text and page_text.strip():
                        extracted_text += f"\n--- PAGE {page_num} ---\n"
                        extracted_text += page_text.strip()
                        extracted_text += "\n"
                except:
                    extracted_text += f"\n--- PAGE {page_num} (EXTRACTION FAILED) ---\n"
                    continue
    except Exception as e:
        raise Exception(f"Failed to open PDF: {str(e)}")
    
    return extracted_text


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text content from a PDF file using multiple fallback methods
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content
        
    Raises:
        Exception: If PDF processing fails
    """
    try:
        logging.info(f"Starting text extraction from PDF: {pdf_path}")
        
        # First try simple extraction method
        try:
            extracted_text = extract_text_from_pdf_simple(pdf_path)
            if extracted_text.strip():
                logging.info(f"Successfully extracted text using simple method")
                return extracted_text.strip()
        except Exception as e:
            logging.warning(f"Simple extraction failed: {str(e)}")
        
        # Fallback to basic pdfplumber with minimal settings
        extracted_text = ""
        
        try:
            with pdfplumber.open(pdf_path, laparams={"detect_vertical": False, "word_margin": 0.1}) as pdf:
                total_pages = len(pdf.pages)
                logging.info(f"PDF has {total_pages} pages - using fallback method")
                
                # Limit to first 20 pages to prevent memory issues
                max_pages = min(total_pages, 20)
                
                for page_num in range(1, max_pages + 1):
                    try:
                        page = pdf.pages[page_num - 1]
                        
                        # Basic text extraction only
                        page_text = page.extract_text(layout=False)
                        
                        if page_text and page_text.strip():
                            extracted_text += f"\n--- PAGE {page_num} ---\n"
                            extracted_text += page_text.strip()
                            extracted_text += "\n"
                        else:
                            extracted_text += f"\n--- PAGE {page_num} (NO TEXT FOUND) ---\n"
                        
                        logging.info(f"Processed page {page_num}/{max_pages}")
                        
                    except Exception as page_error:
                        logging.warning(f"Error processing page {page_num}: {str(page_error)}")
                        extracted_text += f"\n--- PAGE {page_num} (ERROR PROCESSING) ---\n"
                        continue
                
                if total_pages > 20:
                    extracted_text += f"\n--- NOTE: Only first 20 pages processed (total: {total_pages} pages) ---\n"
                    
        except Exception as pdf_error:
            logging.warning(f"Pdfplumber processing failed: {str(pdf_error)}")
        
        # Final fallback: use PyPDF2 for basic text extraction
        if not extracted_text.strip():
            try:
                logging.info("Trying PyPDF2 as final fallback...")
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page_num, page in enumerate(pdf_reader.pages, 1):
                        try:
                            page_text = page.extract_text()
                            if page_text and page_text.strip():
                                extracted_text += f"\n--- PAGE {page_num} ---\n"
                                extracted_text += page_text.strip()
                                extracted_text += "\n"
                            
                            # Limit to 20 pages to prevent memory issues
                            if page_num >= 20:
                                if len(pdf_reader.pages) > 20:
                                    extracted_text += f"\n--- NOTE: Only first 20 pages processed (total: {len(pdf_reader.pages)} pages) ---\n"
                                break
                                
                        except Exception as page_error:
                            logging.warning(f"PyPDF2 error on page {page_num}: {str(page_error)}")
                            extracted_text += f"\n--- PAGE {page_num} (PYPDF2 EXTRACTION FAILED) ---\n"
                            continue
                            
                    if extracted_text.strip():
                        logging.info("Successfully extracted text using PyPDF2 fallback")
                        
            except Exception as pypdf_error:
                logging.error(f"PyPDF2 processing failed: {str(pypdf_error)}")
        
        if not extracted_text.strip():
            raise ValueError("No text content could be extracted from the PDF using any method")
        
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
