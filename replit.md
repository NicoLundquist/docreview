# Replit Configuration for Engineering Compliance Review System

## Overview

The Engineering Compliance Review System is a Flask-based web application that automates the technical review of vendor product specifications against project requirements. The system accepts two PDF documents (project specifications and vendor submittals) and uses OpenAI's GPT-5 API to generate detailed compliance analysis reports following engineering best practices.

The application is designed for professional engineers to streamline the compliance review process, providing systematic evaluation of technical specifications with proper citations, unit conversions, and standardized marking systems for compliance status.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive UI design
- **Static Assets**: CSS and JavaScript files for styling and client-side functionality
- **File Upload Interface**: Drag-and-drop PDF upload with client-side validation
- **Results Display**: Formatted compliance reports with downloadable outputs

### Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Application Structure**: Modular design with separate files for routes, models, and business logic
- **File Processing**: PDF text extraction using pdfplumber library with table detection
- **Session Management**: Flask sessions with configurable secret keys
- **Error Handling**: Comprehensive logging and error tracking throughout the application

### Data Storage Solutions
- **Primary Database**: SQLAlchemy with configurable database URI (defaults to SQLite)
- **Database Models**: ComplianceReview model tracking analysis history, file metadata, and results
- **File Storage**: Local filesystem storage for uploaded PDF documents with secure filename generation
- **Connection Pooling**: Configured with pool recycling and pre-ping for reliability

### Authentication and Authorization Mechanisms
- **Session Security**: Configurable session secret key with environment variable support
- **File Security**: Secure filename generation using UUID prefixes to prevent conflicts
- **Upload Restrictions**: File type validation (PDF only) and size limits (50MB maximum)
- **Path Security**: Werkzeug secure_filename utility for safe file handling

### AI Processing Pipeline
- **OpenAI Integration**: GPT-5 API client for compliance analysis with temperature set to 0 for deterministic results
- **System Prompt**: Comprehensive engineering-focused prompt for technical specification review
- **Text Processing**: Multi-stage PDF text extraction with page markers and table detection
- **Analysis Framework**: Structured compliance evaluation with color-coded status markers (GREEN/YELLOW/RED/GRAY)

## External Dependencies

### Third-Party APIs
- **OpenAI API**: GPT-5 model for automated compliance analysis and report generation
- **API Configuration**: Environment variable-based API key management with fallback handling

### Python Libraries
- **Flask**: Web application framework with SQLAlchemy extension for database operations
- **pdfplumber**: PDF text extraction and table detection library
- **Werkzeug**: WSGI utilities including ProxyFix middleware and secure filename handling
- **OpenAI**: Official Python client library for GPT API integration

### Frontend Dependencies
- **Bootstrap 5**: CSS framework for responsive design and UI components
- **Font Awesome**: Icon library for consistent visual elements throughout the interface
- **Custom CSS/JS**: Application-specific styling and client-side file upload functionality

### Infrastructure Requirements
- **Database**: Configurable database backend (SQLite default, PostgreSQL production-ready)
- **File System**: Local storage for PDF uploads with automatic directory creation
- **Environment Variables**: DATABASE_URL, OPENAI_API_KEY, and SESSION_SECRET for configuration
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies