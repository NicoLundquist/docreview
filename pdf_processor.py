import logging
import pdfplumber

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
        
        # Use timeout and error handling for PDF processing
        with pdfplumber.open(pdf_path, laparams={"detect_vertical": False}) as pdf:
            total_pages = len(pdf.pages)
            logging.info(f"PDF has {total_pages} pages")
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Extract text from the page with error handling
                    page_text = None
                    try:
                        page_text = page.extract_text()
                    except Exception as extract_error:
                        logging.warning(f"Text extraction failed on page {page_num}: {str(extract_error)}")
                        # Try alternative extraction method
                        try:
                            page_text = page.extract_text(layout=False)
                        except:
                            page_text = None
                    
                    if page_text:
                        # Add page marker for reference
                        extracted_text += f"\n--- PAGE {page_num} ---\n"
                        extracted_text += page_text
                        
                        # Try to extract table data if present
                        try:
                            tables = page.extract_tables()
                            if tables:
                                extracted_text += f"\n--- TABLES ON PAGE {page_num} ---\n"
                                for table_num, table in enumerate(tables, 1):
                                    extracted_text += f"\nTable {table_num}:\n"
                                    for row in table:
                                        if row:
                                            # Filter out None values and join
                                            clean_row = [str(cell) if cell is not None else "" for cell in row]
                                            extracted_text += " | ".join(clean_row) + "\n"
                        except Exception as table_error:
                            logging.warning(f"Table extraction failed on page {page_num}: {str(table_error)}")
                    else:
                        extracted_text += f"\n--- PAGE {page_num} (TEXT EXTRACTION FAILED) ---\n"
                    
                    logging.info(f"Processed page {page_num}/{total_pages}")
                    
                except Exception as page_error:
                    logging.warning(f"Error processing page {page_num}: {str(page_error)}")
                    extracted_text += f"\n--- PAGE {page_num} (ERROR PROCESSING) ---\n"
                    continue
        
        if not extracted_text.strip():
            raise ValueError("No text content could be extracted from the PDF")
        
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
