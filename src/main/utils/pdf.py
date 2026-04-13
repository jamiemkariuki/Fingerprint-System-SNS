from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)

# Optional dependency for PDF header overlay
try:
    from pypdf import PdfReader, PdfWriter
    PYPDF_AVAILABLE = True
except ImportError:
    PdfReader = None
    PdfWriter = None
    PYPDF_AVAILABLE = False
    logger.warning("pypdf not installed. PDF header overlay will be disabled.")

# Define Constants
HEADER_PDF_PATH = "st nicholas logo and header.pdf"
DEFAULT_FONT_SIZE = 10
HEADING_FONT_SIZE = 14
TITLE_FONT_SIZE = 18
SPACE_AFTER_HEADING = 12
SPACE_AFTER_TITLE = 30
TABLE_HEADER_BG = colors.grey
TABLE_HEADER_TEXT_COLOR = colors.whitesmoke
TABLE_ROW_BG = colors.beige
TABLE_GRID_COLOR = colors.black


def _get_common_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=TITLE_FONT_SIZE,
        spaceAfter=SPACE_AFTER_TITLE,
        alignment=1  # Center alignment
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=HEADING_FONT_SIZE,
        spaceAfter=SPACE_AFTER_HEADING
    )
    return styles, title_style, heading_style


def _get_table_style(header_cols, row_cols):
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), TABLE_HEADER_TEXT_COLOR),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), DEFAULT_FONT_SIZE),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), TABLE_ROW_BG),
        ('GRID', (0, 0), (-1, -1), 1, TABLE_GRID_COLOR),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ])


def _add_header_to_pdf(generated_pdf_bytes):
    """Helper to overlay the header PDF onto each page of the generated PDF"""
    import os
    
    if not PYPDF_AVAILABLE:
        logger.debug("pypdf not available. Returning plain PDF without header.")
        return generated_pdf_bytes
    
    try:
        # Check if header PDF exists
        if not os.path.exists(HEADER_PDF_PATH):
            logger.error("Header PDF not found at %s. Returning plain PDF.", HEADER_PDF_PATH)
            return generated_pdf_bytes

        header_reader = PdfReader(HEADER_PDF_PATH)
        if not header_reader.pages:
            logger.error("Header PDF is empty. Returning plain PDF.")
            return generated_pdf_bytes

        header_page = header_reader.pages[0]

        generated_reader = PdfReader(BytesIO(generated_pdf_bytes))
        writer = PdfWriter()

        for i, page in enumerate(generated_reader.pages):
            if i == 0:
                page.merge_page(header_page)
            writer.add_page(page)

        output_buffer = BytesIO()
        writer.write(output_buffer)
        return output_buffer.getvalue()
    except Exception as e:
        logger.exception("Error adding header to PDF: %s. Returning plain PDF.", e)
        return generated_pdf_bytes


def generate_attendance_pdf(student, attendance_logs):
    """Generate PDF content for student attendance report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles, title_style, heading_style = _get_common_styles()
        
        story = []
        
        # Add top spacer to avoid collision with header (approx 1.5 inches)
        story.append(Spacer(1, 1.5*inch))
        
        story.append(Paragraph("Student Attendance Report", title_style))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("Student Information", heading_style))
        student_info = [
            ["Name:", student["name"]],
            ["Class:", student["class"]],
            ["Student ID:", str(student["id"])],
            ["Fingerprint ID:", str(student["fingerprint_id"]) if student["fingerprint_id"] else "Not assigned"]
        ]
        
        student_table = Table(student_info, colWidths=[1.5*inch, 3*inch])
        student_table.setStyle(_get_table_style(2, 2))
        story.append(student_table)
        story.append(Spacer(1, 20))
        
        total_days = len(attendance_logs)
        story.append(Paragraph(f"Attendance Summary ({total_days} days recorded)", heading_style))
        
        if attendance_logs:
            table_data = [["Date", "Scans", "First Scan", "Last Scan"]]
            
            for log in attendance_logs:
                # Handle First Scan
                first_scan_str = ""
                if isinstance(log["first_scan"], timedelta):
                    total_seconds = int(log["first_scan"].total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    first_scan_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                elif hasattr(log["first_scan"], 'strftime'):
                    first_scan_str = log["first_scan"].strftime("%H:%M:%S")
                else:
                    first_scan_str = str(log["first_scan"])

                # Handle Last Scan
                last_scan_str = ""
                if isinstance(log["last_scan"], timedelta):
                    total_seconds = int(log["last_scan"].total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    last_scan_str = f"{hours:02}:{minutes:02}:{seconds:02}"
                elif hasattr(log["last_scan"], 'strftime'):
                    last_scan_str = log["last_scan"].strftime("%H:%M:%S")
                else:
                    last_scan_str = str(log["last_scan"])

                table_data.append([
                    log["date"].strftime("%Y-%m-%d"),
                    str(log["scan_count"]),
                    first_scan_str,
                    last_scan_str
                ])
            
            attendance_table = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 1.2*inch, 1.2*inch])
            attendance_table.setStyle(_get_table_style(4, 4))
            story.append(attendance_table)
        else:
            story.append(Paragraph("No attendance records found.", styles['Normal']))
        
        doc.build(story)
        return _add_header_to_pdf(buffer.getvalue())
    except Exception as e:
        logger.exception("Error generating student attendance PDF: %s", e)
        raise


def generate_class_attendance_pdf(class_name, students, date):
    """Generate PDF content for class attendance report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles, title_style, heading_style = _get_common_styles()
        
        story = []
        
        # Add top spacer to avoid collision with header (approx 1.5 inches)
        story.append(Spacer(1, 1.5*inch))
        
        story.append(Paragraph(f"Class Attendance Report - {class_name} ({date.strftime('%Y-%m-%d')})", title_style))
        story.append(Spacer(1, 20))
        
        if students:
            table_data = [["Name", "Status"]]
            
            for student in students:
                table_data.append([
                    student["name"],
                    student["status"]
                ])
            
            attendance_table = Table(table_data, colWidths=[2*inch, 1.5*inch])
            attendance_table.setStyle(_get_table_style(2, 2))
            story.append(attendance_table)
        else:
            story.append(Paragraph("No students found for this class.", styles['Normal']))
        
        doc.build(story)
        return _add_header_to_pdf(buffer.getvalue())
    except Exception as e:
        logger.exception("Error generating class attendance PDF: %s", e)
        raise


def generate_audit_report_pdf(student, audit_records):
    """Generate PDF content for student clearance/audit report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles, title_style, heading_style = _get_common_styles()
        
        story = []
        
        # Add top spacer to avoid collision with header (approx 1.5 inches)
        story.append(Spacer(1, 1.5*inch))
        
        # Title
        story.append(Paragraph("Student Clearance Certificate", title_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Student Info
        story.append(Paragraph("Student Information", heading_style))
        student_info = [
            ["Name:", student["name"]],
            ["Class:", student["class"]],
            ["Student ID:", str(student["id"])]
        ]
        
        student_table = Table(student_info, colWidths=[1.5*inch, 4*inch])
        student_table.setStyle(_get_table_style(2, 2))
        story.append(student_table)
        story.append(Spacer(1, 30))
        
        # Audit Records
        story.append(Paragraph("Clearance Summary", heading_style))
        
        if audit_records:
            table_data = [["Subject", "Status", "Remarks / Notes"]]
            
            for record in audit_records:
                status_text = record["status"]
                remarks = record["notes"] if record["notes"] else "-"
                
                table_data.append([
                    record["subject_name"],
                    status_text,
                    Paragraph(remarks, styles['Normal']) # Use Paragraph for wrapping notes
                ])
            
            audit_table = Table(table_data, colWidths=[1.5*inch, 1*inch, 3*inch])
            audit_table.setStyle(_get_table_style(3, 3))
            story.append(audit_table)
        else:
            story.append(Paragraph("No clearance records found for this student.", styles['Normal']))
        
        story.append(Spacer(1, 40))
        story.append(Paragraph("Official School Stamp & Signature:", styles['Normal']))
        story.append(Spacer(1, 50))
        story.append(Paragraph("________________________________________", styles['Normal']))
        story.append(Paragraph("Head of Department / Bursar", styles['Normal']))

        doc.build(story)
        return _add_header_to_pdf(buffer.getvalue())
    except Exception as e:
        logger.exception("Error generating audit report PDF: %s", e)
        raise


def generate_exam_results_pdf(student, exam_results):
    """Generate PDF content for student exam results report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles, title_style, heading_style = _get_common_styles()
        
        story = []
        
        # Add top spacer to avoid collision with header (approx 1.5 inches)
        story.append(Spacer(1, 1.5*inch))
        
        # Title
        story.append(Paragraph("Student Performance Report - Exam Results", title_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Student Info
        story.append(Paragraph("Student Information", heading_style))
        student_info = [
            ["Name:", student["name"]],
            ["Class:", student["class"]],
            ["Student ID:", str(student["id"])]
        ]
        
        student_table = Table(student_info, colWidths=[1.5*inch, 4*inch])
        student_table.setStyle(_get_table_style(2, 2))
        story.append(student_table)
        story.append(Spacer(1, 30))
        
        # Results Table
        story.append(Paragraph("Academic Performance Summary", heading_style))
        
        if exam_results:
            table_data = [["Subject", "Term - Type", "Score", "Grade", "Remarks"]]
            
            for res in exam_results:
                subject_name = res["subject_name"]
                term_type = f"{res['term']} - {res['exam_type']}"
                score_str = f"{res['score']} / {res['max_score']}"
                grade = res["grade"] if res["grade"] else "-"
                remarks = res["remarks"] if res["remarks"] else "-"
                
                table_data.append([
                    subject_name,
                    term_type,
                    score_str,
                    grade,
                    Paragraph(remarks, styles['Normal'])
                ])
            
            results_table = Table(table_data, colWidths=[1.5*inch, 1.2*inch, 0.8*inch, 0.5*inch, 1.6*inch])
            results_table.setStyle(_get_table_style(5, 5))
            story.append(results_table)
        else:
            story.append(Paragraph("No exam results found for this student.", styles['Normal']))
        
        story.append(Spacer(1, 40))
        story.append(Paragraph("Official School Stamp & Signature:", styles['Normal']))
        story.append(Spacer(1, 50))
        story.append(Paragraph("________________________________________", styles['Normal']))
        story.append(Paragraph("Head Teacher / Academic Registrar", styles['Normal']))

        doc.build(story)
        return _add_header_to_pdf(buffer.getvalue())
    except Exception as e:
        logger.exception("Error generating exam results PDF: %s", e)
        raise
