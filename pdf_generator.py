"""
PDF Generation for Compliance Reports
Converts markdown-formatted compliance reports to professional PDFs
"""

import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import markdown
import logging


def generate_compliance_pdf(report_content, review_data):
    """
    Generate a professional PDF from compliance report content
    
    Args:
        report_content (str): Markdown-formatted compliance report
        review_data (dict): Review metadata (id, filenames, date, etc.)
    
    Returns:
        bytes: PDF content as bytes
    """
    # Create a BytesIO buffer to hold the PDF
    buffer = io.BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    # Get default styles and create custom ones
    styles = getSampleStyleSheet()
    
    # Custom styles for professional look
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=20,
        textColor=colors.HexColor('#1e3a8a'),
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=16,
        textColor=colors.HexColor('#1e3a8a'),
        borderWidth=1,
        borderColor=colors.HexColor('#e2e8f0'),
        borderPadding=8,
        backColor=colors.HexColor('#f8fafc')
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=12,
        textColor=colors.HexColor('#374151'),
        leftIndent=12
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=colors.HexColor('#1f2937'),
        alignment=TA_JUSTIFY
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=12,
        textColor=colors.HexColor('#1f2937')
    )
    
    # Build the story (content) for the PDF
    story = []
    
    # Header section
    story.append(Paragraph("Engineering Compliance Review Report", title_style))
    story.append(Spacer(1, 12))
    
    # Document information table
    doc_info = [
        ['Report ID:', str(review_data.get('id', 'N/A'))],
        ['Analysis Date:', review_data.get('created_at', 'N/A')],
        ['Project Specification:', review_data.get('project_spec_filename', 'N/A')],
        ['Vendor Submittal:', review_data.get('submittal_filename', 'N/A')],
        ['Overall Status:', review_data.get('overall_status', 'N/A')],
        ['Models Reviewed:', str(review_data.get('models_reviewed', 'N/A'))],
        ['Compliant Models:', str(review_data.get('compliant_models', 'N/A'))]
    ]
    
    doc_table = Table(doc_info, colWidths=[2*inch, 4*inch])
    doc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(doc_table)
    story.append(Spacer(1, 20))
    
    # Process the report content
    processed_content = process_markdown_for_pdf(report_content)
    
    # Convert processed content to PDF elements
    for element in processed_content:
        if element['type'] == 'heading1':
            story.append(Paragraph(element['content'], heading_style))
        elif element['type'] == 'heading2':
            story.append(Paragraph(element['content'], subheading_style))
        elif element['type'] == 'heading3':
            story.append(Paragraph(element['content'], subheading_style))
        elif element['type'] == 'paragraph':
            story.append(Paragraph(element['content'], body_style))
        elif element['type'] == 'bullet':
            story.append(Paragraph(f"• {element['content']}", bullet_style))
        elif element['type'] == 'spacer':
            story.append(Spacer(1, 12))
    
    # Footer
    story.append(Spacer(1, 20))
    footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} by Engineering Compliance Review System"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(footer_text, footer_style))
    
    # Build the PDF
    doc.build(story)
    
    # Get the PDF content
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content


def process_markdown_for_pdf(content):
    """
    Process markdown content and convert to structured data for PDF generation
    """
    elements = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
            elements.append({'type': 'spacer', 'content': ''})
            continue
            
        # Headers
        if line.startswith('# '):
            elements.append({'type': 'heading1', 'content': format_compliance_badges(line[2:])})
        elif line.startswith('## '):
            elements.append({'type': 'heading2', 'content': format_compliance_badges(line[3:])})
        elif line.startswith('### '):
            elements.append({'type': 'heading3', 'content': format_compliance_badges(line[4:])})
        # Bullet points
        elif line.startswith('* '):
            elements.append({'type': 'bullet', 'content': format_compliance_badges(line[2:])})
        elif line.startswith('- '):
            elements.append({'type': 'bullet', 'content': format_compliance_badges(line[2:])})
        # Regular paragraphs
        else:
            elements.append({'type': 'paragraph', 'content': format_compliance_badges(line)})
    
    return elements


def format_compliance_badges(text):
    """
    Convert compliance status markers to HTML with colors for PDF
    """
    # Handle detailed compliance markers
    text = re.sub(r'\[GREEN:([^\]]+)\]', r'<font color="#10b981"><b>[GREEN:\1]</b></font>', text)
    text = re.sub(r'\[YELLOW:([^\]]+)\]', r'<font color="#f59e0b"><b>[YELLOW:\1]</b></font>', text)
    text = re.sub(r'\[RED:([^\]]+)\]', r'<font color="#ef4444"><b>[RED:\1]</b></font>', text)
    text = re.sub(r'\[GRAY:([^\]]+)\]', r'<font color="#6b7280"><b>[GRAY:\1]</b></font>', text)
    
    # Handle simple compliance markers as fallback
    text = re.sub(r'\[GREEN\]', r'<font color="#10b981"><b>[GREEN]</b></font>', text)
    text = re.sub(r'\[YELLOW\]', r'<font color="#f59e0b"><b>[YELLOW]</b></font>', text)
    text = re.sub(r'\[RED\]', r'<font color="#ef4444"><b>[RED]</b></font>', text)
    text = re.sub(r'\[GRAY\]', r'<font color="#6b7280"><b>[GRAY]</b></font>', text)
    
    # Format bold text
    text = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*([^*]+)\*', r'<i>\1</i>', text)
    
    return text