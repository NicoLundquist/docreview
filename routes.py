import os
import logging
from flask import render_template, request, flash, redirect, url_for, jsonify, make_response
from werkzeug.utils import secure_filename
from app import app, db
from models import ComplianceReview
from pdf_processor import extract_text_from_pdf
from compliance_analyzer import analyze_compliance
import uuid

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main page with file upload form"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and initiate compliance analysis"""
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
            
            # Update database record with results
            review.report_content = analysis_result
            review.status = 'completed'
            
            # Try to extract summary data (basic parsing)
            lines = analysis_result.split('\n') if analysis_result else []
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
            
            flash('Compliance analysis completed successfully!', 'success')
            return redirect(url_for('view_results', review_id=review.id))
            
        except Exception as e:
            logging.error(f"Error during analysis: {str(e)}")
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
def view_results(review_id):
    """Display compliance analysis results"""
    review = ComplianceReview.query.get_or_404(review_id)
    
    if review.status == 'error':
        flash(f'Analysis failed: {review.error_message}', 'error')
        return redirect(url_for('index'))
    
    if review.status == 'pending':
        flash('Analysis is still in progress. Please wait...', 'info')
        return redirect(url_for('index'))
    
    return render_template('results.html', review=review)

@app.route('/download/<int:review_id>')
def download_report(review_id):
    """Download compliance report as text file"""
    review = ComplianceReview.query.get_or_404(review_id)
    
    if review.status != 'completed' or not review.report_content:
        flash('Report not available', 'error')
        return redirect(url_for('index'))
    
    response = make_response(review.report_content)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=compliance_report_{review_id}.txt'
    
    return response

@app.route('/history')
def view_history():
    """View past compliance reviews"""
    reviews = ComplianceReview.query.order_by(ComplianceReview.created_at.desc()).limit(20).all()
    return render_template('history.html', reviews=reviews)

@app.errorhandler(413)
def too_large(e):
    flash('File too large. Maximum size is 50MB.', 'error')
    return redirect(url_for('index'))
