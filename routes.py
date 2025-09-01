import os
import logging
from flask import render_template, request, flash, redirect, url_for, jsonify, make_response, session
from werkzeug.utils import secure_filename
from flask_login import current_user
from app import app, db
from models import ComplianceReview
from pdf_processor import extract_text_from_pdf
from compliance_analyzer import analyze_compliance
from pdf_generator import generate_compliance_pdf
from replit_auth import require_login, make_replit_blueprint
import uuid

# Register authentication blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page with file upload form or login landing"""
    if current_user.is_authenticated:
        return render_template('index.html')
    else:
        return render_template('landing.html')

@app.route('/upload', methods=['POST'])
@require_login
def upload_files():
    """Handle file upload and initiate compliance analysis"""
    # Set a longer timeout for this specific route
    from flask import g
    g.request_timeout = 1200  # 20 minutes
    
    try:
        # Check if files were uploaded
        if 'project_spec' not in request.files or 'vendor_submittal' not in request.files:
            flash('Please upload both Project Specification and Vendor Submittal files', 'error')
            return redirect(url_for('index'))
        
        project_spec_file = request.files['project_spec']
        vendor_submittal_file = request.files['vendor_submittal']
        
        # Validate files
        if project_spec_file.filename == '' or vendor_submittal_file.filename == '':
            flash('Please select both files', 'error')
            return redirect(url_for('index'))
        
        if not (allowed_file(project_spec_file.filename) and allowed_file(vendor_submittal_file.filename)):
            flash('Only PDF files are allowed', 'error')
            return redirect(url_for('index'))
        
        # Generate unique filenames
        project_spec_filename = secure_filename(f"{uuid.uuid4()}_{project_spec_file.filename}")
        vendor_submittal_filename = secure_filename(f"{uuid.uuid4()}_{vendor_submittal_file.filename}")
        
        # Save files
        project_spec_path = os.path.join(app.config['UPLOAD_FOLDER'], project_spec_filename)
        vendor_submittal_path = os.path.join(app.config['UPLOAD_FOLDER'], vendor_submittal_filename)
        
        project_spec_file.save(project_spec_path)
        vendor_submittal_file.save(vendor_submittal_path)
        
        # Create database record
        review = ComplianceReview()
        review.project_spec_filename = project_spec_file.filename
        review.submittal_filename = vendor_submittal_file.filename
        review.status = 'pending'
        review.user_id = current_user.id  # Associate with current user
        db.session.add(review)
        db.session.commit()
        
        try:
            # Extract text from PDFs
            logging.info("Extracting text from Project Specification...")
            project_spec_text = extract_text_from_pdf(project_spec_path)
            
            logging.info("Extracting text from Vendor Submittal...")
            vendor_submittal_text = extract_text_from_pdf(vendor_submittal_path)
            
            if not project_spec_text.strip():
                raise ValueError("Could not extract text from Project Specification PDF")
            
            if not vendor_submittal_text.strip():
                raise ValueError("Could not extract text from Vendor Submittal PDF")
            
            logging.info("Starting compliance analysis...")
            # Perform compliance analysis
            analysis_result = analyze_compliance(project_spec_text, vendor_submittal_text)
            
            # Clean the AI response output to remove any remaining Unicode characters
            def clean_ai_output(text):
                if not text:
                    return ""
                
                # Replace common Unicode characters that might slip through
                replacements = {
                    '\u2011': '-',  # non-breaking hyphen
                    '\u2013': '-',  # en dash
                    '\u2014': '--', # em dash
                    '\u2019': "'",  # right single quote
                    '\u2018': "'",  # left single quote
                    '\u201c': '"',  # left double quote
                    '\u201d': '"',  # right double quote
                    '\u2026': '...',# ellipsis
                    '\u00b0': ' deg', # degree
                    '\u00a0': ' ',  # non-breaking space
                    '\u2032': "'",  # prime
                    '\u2033': '"',  # double prime
                }
                
                for old, new in replacements.items():
                    text = text.replace(old, new)
                
                # Convert to ASCII, ignoring any remaining problematic characters
                try:
                    text = text.encode('ascii', errors='ignore').decode('ascii')
                except:
                    # Fallback: manually strip non-ASCII characters
                    text = ''.join(ch for ch in text if ord(ch) < 128)
                
                return text
            
            # Clean the analysis result before saving
            cleaned_analysis_result = clean_ai_output(analysis_result)
            
            # Update database record with results
            review.report_content = cleaned_analysis_result
            review.status = 'completed'
            
            # Debug: Show what we're saving to database
            logging.info("=" * 80)
            logging.info("SAVING TO DATABASE:")
            logging.info(f"Review ID: {review.id}")
            logging.info(f"Status: {review.status}")
            logging.info(f"Original report length: {len(analysis_result) if analysis_result else 0}")
            logging.info(f"Cleaned report length: {len(cleaned_analysis_result) if cleaned_analysis_result else 0}")
            logging.info(f"Report content first 500 chars: {cleaned_analysis_result[:500] if cleaned_analysis_result else 'None'}")
            logging.info("=" * 80)
            
            # Try to extract summary data (basic parsing)
            lines = cleaned_analysis_result.split('\n') if cleaned_analysis_result else []
            for line in lines:
                if 'Overall compliance status' in line:
                    review.overall_status = line.split(':')[-1].strip().strip('*[]')
                elif 'Number of models reviewed' in line:
                    try:
                        review.models_reviewed = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                    except:
                        pass
                elif 'Number of compliant models identified' in line:
                    try:
                        review.compliant_models = int(''.join(filter(str.isdigit, line.split(':')[-1])))
                    except:
                        pass
            
            db.session.commit()
            
            # Debug: Verify what was actually saved
            logging.info("=" * 80)
            logging.info("VERIFICATION AFTER DATABASE COMMIT:")
            fresh_review = ComplianceReview.query.get(review.id)
            if fresh_review:
                logging.info(f"Fresh review status: {fresh_review.status}")
                logging.info(f"Fresh review report content length: {len(fresh_review.report_content) if fresh_review.report_content else 0}")
                logging.info(f"Fresh review overall status: {fresh_review.overall_status}")
            else:
                logging.error("Could not retrieve fresh review from database!")
            logging.info("=" * 80)
            
            flash('Compliance analysis completed successfully!', 'success')
            return redirect(url_for('view_results', review_id=review.id))
            
        except Exception as e:
            logging.error(f"Error during analysis: {str(e)}")
            # Rollback the transaction to clear any previous errors
            db.session.rollback()
            review.status = 'error'
            review.error_message = str(e)
            db.session.commit()
            flash(f'Error during analysis: {str(e)}', 'error')
            return redirect(url_for('index'))
        
        finally:
            # Clean up uploaded files
            try:
                os.remove(project_spec_path)
                os.remove(vendor_submittal_path)
            except:
                pass
                
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        flash(f'Upload error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/results/<int:review_id>')
@require_login
def view_results(review_id):
    """Display compliance analysis results"""
    review = ComplianceReview.query.filter_by(id=review_id, user_id=current_user.id).first_or_404()
    
    # Debug: Show what we're displaying
    logging.info("=" * 80)
    logging.info(f"DISPLAYING RESULTS FOR REVIEW {review_id}:")
    logging.info(f"Status: {review.status}")
    logging.info(f"Report content length: {len(review.report_content) if review.report_content else 0}")
    logging.info(f"Overall status: {review.overall_status}")
    logging.info(f"Models reviewed: {review.models_reviewed}")
    logging.info(f"Compliant models: {review.compliant_models}")
    if review.report_content:
        logging.info(f"Report content first 500 chars: {review.report_content[:500]}")
    else:
        logging.info("NO REPORT CONTENT FOUND!")
    logging.info("=" * 80)
    
    if review.status == 'error':
        flash(f'Analysis failed: {review.error_message}', 'error')
        return redirect(url_for('index'))
    
    if review.status == 'pending':
        flash('Analysis is still in progress. Please wait...', 'info')
        return redirect(url_for('index'))
    
    return render_template('results.html', review=review)

@app.route('/download/<int:review_id>')
@require_login
def download_report(review_id):
    """Download compliance report as formatted PDF"""
    review = ComplianceReview.query.filter_by(id=review_id, user_id=current_user.id).first_or_404()
    
    if review.status != 'completed' or not review.report_content:
        flash('Report not available', 'error')
        return redirect(url_for('index'))
    
    try:
        # Prepare review data for PDF generation
        review_data = {
            'id': review.id,
            'created_at': review.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if review.created_at else 'N/A',
            'project_spec_filename': review.project_spec_filename or 'N/A',
            'submittal_filename': review.submittal_filename or 'N/A',
            'overall_status': review.overall_status or 'N/A',
            'models_reviewed': review.models_reviewed,
            'compliant_models': review.compliant_models
        }
        
        # Generate PDF
        pdf_content = generate_compliance_pdf(review.report_content, review_data)
        
        # Create response with PDF
        response = make_response(pdf_content)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=compliance_report_{review_id}.pdf'
        
        return response
        
    except Exception as e:
        logging.error(f"PDF generation error: {str(e)}")
        flash('Error generating PDF report', 'error')
        return redirect(url_for('view_results', review_id=review_id))

@app.route('/history')
@require_login
def view_history():
    """View past compliance reviews"""
    reviews = ComplianceReview.query.filter_by(user_id=current_user.id).order_by(ComplianceReview.created_at.desc()).limit(20).all()
    return render_template('history.html', reviews=reviews)

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 50MB.', 'error')
    return redirect(url_for('index'))
