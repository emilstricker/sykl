from flask import Flask, render_template, request, jsonify, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, Image, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from io import BytesIO
import os
import google.generativeai as genai
import json
import re
import zipfile
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configure Gemini AI
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Create the Gemini model
generation_config = {
    "temperature": 0.9,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

# Initialize chat history with system prompt
SYSTEM_PROMPT = """Du er en hjælpsom matematiklærer, der genererer opgaveark. 
Generer to forskellige versioner af opgaven (SYKL-DEL A og SYKL-DEL B).

VIGTIGT: Du skal returnere et validt JSON-objekt i præcis dette format uden ekstra tekst eller forklaringer:
{
    "worksheets": [
        {
            "opgave_number": "1",
            "title": "Titel på opgaven",
            "materials": "Liste af materialer",
            "main_question": "Hovedspørgsmålet",
            "sykl_del_type": "A",
            "sykl_del_a": "Beskrivelse af opgaven",
            "bullet_points": "• Punkt 1\\n• Punkt 2\\n• Punkt 3",
            "tips_1": "Første tip",
            "tips_2": "Andet tip",
            "tips_3": "Tredje tip"
        },
        {
            "opgave_number": "1",
            "title": "Titel på opgaven",
            "materials": "Liste af materialer",
            "main_question": "Hovedspørgsmålet",
            "sykl_del_type": "B",
            "sykl_del_a": "Beskrivelse af opgaven",
            "bullet_points": "• Punkt 1\\n• Punkt 2\\n• Punkt 3",
            "tips_1": "Første tip",
            "tips_2": "Andet tip",
            "tips_3": "Tredje tip"
        }
    ]
}

HUSK:
1. Alle felter skal være strenge (strings)
2. Brug \\n for linjeskift i bullet_points
3. Start bullet points med •
4. Returner KUN JSON uden ekstra tekst eller forklaringer"""

chat_history = [
    {"role": "user", "parts": [SYSTEM_PROMPT]},
    {"role": "model", "parts": ["Jeg vil hjælpe med at generere opgaveark i det ønskede format med både SYKL-DEL A og B versioner. Jeg vil sørge for at opgaverne er på dansk, alderstilpassede og har en naturlig progression i sværhedsgrad mellem de to versioner."]}
]

class RoundedBox(Flowable):
    def __init__(self, width, height, content_list, padding=10, radius=10, background_color=colors.white):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.content_list = content_list
        self.padding = padding
        self.radius = radius
        self.background_color = background_color

    def draw(self):
        # Draw rounded rectangle
        self.canv.saveState()
        
        # Draw background
        p = self.canv.beginPath()
        p.roundRect(0, 0, self.width, self.height, self.radius)
        self.canv.setFillColor(self.background_color)
        self.canv.setStrokeColor(self.background_color)  # Make border same as background
        self.canv.setLineWidth(1)
        self.canv.drawPath(p, fill=1, stroke=1)
        
        # Draw content
        y = self.height - self.padding
        
        # Calculate total content height
        total_height = 0
        for content in self.content_list:
            content.wrapOn(self.canv, self.width - 2*self.padding, y)
            total_height += content.height + 5  # 5 points spacing between items
        
        # Start drawing from top, centered vertically if there's extra space
        y = self.height - self.padding - (self.height - 2*self.padding - total_height)/2
        
        for content in self.content_list:
            content.wrapOn(self.canv, self.width - 2*self.padding, y)
            content.drawOn(self.canv, self.padding, y - content.height)
            y -= content.height + 5  # 5 points spacing between items
        
        self.canv.restoreState()

def split_bullet_points(bullet_points):
    """Split bullet points that are separated by either newlines or dots"""
    if not bullet_points:
        return []
    
    # First replace escaped newlines with actual newlines
    bullet_points = bullet_points.replace('\\n', '\n')
    
    # Split on either newlines or dots followed by bullet points
    points = re.split(r'\n|(?<=\S)\s*•\s+', bullet_points)
    
    # Clean up each point
    cleaned_points = []
    for point in points:
        point = point.strip()
        if point:
            # Remove leading bullet if present
            point = point.lstrip('•').strip()
            if point:
                cleaned_points.append(point)
    
    return cleaned_points

def create_pdf(worksheet_data):
    # Create the PDF object
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30*mm,
        leftMargin=30*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # Define colors
    sykl_green = colors.HexColor('#4A7C59')  # Dark green for headers
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Header style (MATEMATIK OPGAVEARK)
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=5*mm,
        alignment=1,  # Center alignment
        fontName='Helvetica'
    )
    
    # Title style (e.g. "HVOR MANGE PERLER?")
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=sykl_green,
        spaceAfter=10*mm,
        fontName='Helvetica-Bold'
    )
    
    # Section header style (e.g. "SYKL-DEL A:")
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=sykl_green,
        spaceBefore=5*mm,
        spaceAfter=3*mm,
        fontName='Helvetica-Bold'
    )
    
    # Normal text style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=3*mm,
        leading=16,
        fontName='Helvetica'
    )
    
    # Bullet point style
    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=styles['Normal'],
        fontSize=12,
        leftIndent=20,
        spaceAfter=3*mm,
        leading=16,
        fontName='Helvetica'
    )
    
    # Tips box style
    tips_style = ParagraphStyle(
        'CustomTips',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.white,
        spaceAfter=2*mm,
        leading=14,
        fontName='Helvetica'
    )
    
    # Story (content)
    story = []
    
    # Add logo
    logo_path = os.path.join('static', 'images', 'sykl-logo-300x262.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=20*mm, height=17.5*mm)
        story.append(logo)
    
    # Header
    header_text = 'MATEMATIK<br/><font color="#4A7C59" size="16">OPGAVEARK</font>'
    story.append(Paragraph(header_text, header_style))
    story.append(Spacer(1, 5*mm))
    
    # Title
    story.append(Paragraph(worksheet_data['title'].upper(), title_style))
    
    # Materials
    story.append(Paragraph(f"<b>Materialer:</b> {worksheet_data['materials']}", normal_style))
    
    # SYKL-DEL section
    story.append(Paragraph(f"SYKL-DEL {worksheet_data['sykl_del_type']}:", section_style))
    
    # Main task description
    description = worksheet_data['sykl_del_a'].replace('\\n', '<br/>')
    story.append(Paragraph(description, normal_style))
    
    # Bullet points
    if worksheet_data['bullet_points']:
        bullet_points = split_bullet_points(worksheet_data['bullet_points'])
        if bullet_points:
            items = [ListItem(Paragraph(point, bullet_style)) for point in bullet_points]
            story.append(ListFlowable(
                items,
                bulletType='bullet',
                start='•',
                bulletFontSize=12,
                leftIndent=20,
                bulletOffsetY=2
            ))
    
    # Tips box with scissors decoration
    if any(worksheet_data.get(f'tips_{i}', '').strip() for i in range(1, 4)):
        # Create tips box with rounded corners and green background
        tips_box = []
        
        # Add tips
        for i in range(1, 4):
            tip = worksheet_data.get(f'tips_{i}', '').strip()
            if tip:
                tip_text = f"MATEMA-TIPS {worksheet_data['opgave_number']}.{i}:<br/>{tip}"
                tips_box.append(Paragraph(tip_text, tips_style))
        
        if tips_box:
            # Create a table for the tips box
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), sykl_green),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ])
            
            # Create the table with tips
            tips_table = Table([[tip] for tip in tips_box], colWidths=[doc.width * 0.8])
            tips_table.setStyle(table_style)
            
            # Add some space before the tips box
            story.append(Spacer(1, 10*mm))
            story.append(tips_table)
    
    # Add footer
    footer_text = f"SYKL • MATEMATIK • 3.-4. KLASSE • KP DK/SYKL"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.black,
        alignment=1,  # Center
        spaceBefore=15*mm
    )
    story.append(Paragraph(footer_text, footer_style))
    
    # Add page number
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 10)
        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin,
            doc.bottomMargin,
            str(canvas.getPageNumber())
        )
        canvas.restoreState()
    
    # Build PDF with page numbers
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer

def normalize_text(text):
    """Normalize text by cleaning whitespace and newlines"""
    if not text:
        return ''
    
    # Convert text to string if it isn't already
    text = str(text)
    
    # Replace literal newlines with spaces
    text = text.replace('\n', ' ').replace('\r', '')
    
    # Clean up any double spaces
    text = ' '.join(text.split())
    
    # Replace escaped newlines with actual newlines for processing
    text = text.replace('\\n', '\n')
    
    # Clean up the text
    text = text.strip()
    
    # Convert back to escaped newlines for JSON
    text = text.replace('\n', '\\n')
    
    return text

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            # Get form data
            opgave_number = request.form.get('opgave_number', '')
            title = request.form.get('title', '')
            materials = request.form.get('materials', '')
            main_question = request.form.get('main_question', '')
            sykl_del_type = request.form.get('sykl_del_type', '')
            sykl_del_a = request.form.get('sykl_del_a', '')
            bullet_points = request.form.get('bullet_points', '')
            tips_1 = request.form.get('tips_1', '')
            tips_2 = request.form.get('tips_2', '')
            tips_3 = request.form.get('tips_3', '')

            # Debug print
            print("Received form data:")
            print(f"opgave_number: {opgave_number}")
            print(f"title: {title}")
            print(f"materials: {materials}")
            print(f"main_question: {main_question}")
            print(f"sykl_del_type: {sykl_del_type}")
            print(f"sykl_del_a: {sykl_del_a}")
            print(f"bullet_points: {bullet_points}")
            print(f"tips_1: {tips_1}")
            print(f"tips_2: {tips_2}")
            print(f"tips_3: {tips_3}")

            # Create PDF
            pdf_buffer = create_pdf({
                'opgave_number': opgave_number,
                'title': title,
                'materials': materials,
                'main_question': main_question,
                'sykl_del_type': sykl_del_type,
                'sykl_del_a': sykl_del_a,
                'bullet_points': bullet_points,
                'tips_1': tips_1,
                'tips_2': tips_2,
                'tips_3': tips_3
            })

            # Send PDF
            opgave_num = opgave_number
            del_type = sykl_del_type.lower()
            filename = f'opgave_{opgave_num}{del_type}.pdf'
            return send_file(
                pdf_buffer,
                download_name=filename,
                as_attachment=True,
                mimetype='application/pdf'
            )

        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return f"Error generating PDF: {str(e)}", 500

    return render_template('index.html')

@app.route('/export', methods=['POST'])
def export_worksheet():
    try:
        # Get worksheet data from request
        worksheet_data = request.get_json()
        if not worksheet_data:
            return jsonify({'error': 'No data provided'}), 400

        # Log the received data for debugging
        print("Received worksheet data:", worksheet_data)

        # Ensure all fields exist with default values
        worksheet_data = {
            'opgave_number': str(worksheet_data.get('opgave_number', '1')),
            'title': str(worksheet_data.get('title', '')).strip(),
            'materials': str(worksheet_data.get('materials', '')).strip(),
            'main_question': str(worksheet_data.get('main_question', '')).strip(),
            'sykl_del_type': str(worksheet_data.get('sykl_del_type', 'A')).strip(),
            'sykl_del_a': str(worksheet_data.get('sykl_del_a', '')).strip(),
            'bullet_points': str(worksheet_data.get('bullet_points', '')).strip(),
            'tips_1': str(worksheet_data.get('tips_1', '')).strip(),
            'tips_2': str(worksheet_data.get('tips_2', '')).strip(),
            'tips_3': str(worksheet_data.get('tips_3', '')).strip()
        }

        # Create PDF
        pdf_buffer = create_pdf(worksheet_data)
        
        # Generate filename based on opgave number and SYKL-DEL type
        opgave_num = worksheet_data['opgave_number']
        del_type = worksheet_data['sykl_del_type'].lower()
        filename = f'opgave_{opgave_num}{del_type}.pdf'

        # Send file
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Error in export_worksheet: {str(e)}")
        print("Received data:", worksheet_data)  # Debug print
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/export_all_worksheets', methods=['POST'])
def export_all_worksheets():
    try:
        data = request.get_json()
        if not data or 'worksheets' not in data:
            return jsonify({'error': 'No worksheet data provided'}), 400

        # Create a ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for worksheet in data['worksheets']:
                try:
                    # Ensure all fields exist with default values
                    worksheet_data = {
                        'opgave_number': str(worksheet.get('opgave_number', '1')),
                        'title': str(worksheet.get('title', '')).strip(),
                        'materials': str(worksheet.get('materials', '')).strip(),
                        'main_question': str(worksheet.get('main_question', '')).strip(),
                        'sykl_del_type': str(worksheet.get('sykl_del_type', 'A')).strip(),
                        'sykl_del_a': str(worksheet.get('sykl_del_a', '')).strip(),
                        'bullet_points': str(worksheet.get('bullet_points', '')).strip(),
                        'tips_1': str(worksheet.get('tips_1', '')).strip(),
                        'tips_2': str(worksheet.get('tips_2', '')).strip(),
                        'tips_3': str(worksheet.get('tips_3', '')).strip()
                    }

                    # Create PDF for this worksheet
                    pdf_buffer = create_pdf(worksheet_data)
                    
                    # Generate filename for this worksheet
                    opgave_num = worksheet_data['opgave_number']
                    del_type = worksheet_data['sykl_del_type'].lower()
                    filename = f'opgave_{opgave_num}{del_type}.pdf'
                    
                    # Add PDF to ZIP
                    zip_file.writestr(filename, pdf_buffer.getvalue())
                except Exception as e:
                    print(f"Error processing worksheet: {str(e)}")
                    continue

        # Prepare ZIP file for sending
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name='opgaver.zip'
        )

    except Exception as e:
        print(f"Error in export_all_worksheets: {str(e)}")
        print("Received data:", request.get_json())  # Debug print
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate_worksheet():
    try:
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        try:
            response = model.generate_content([
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "user", "parts": [f"Generer et opgaveark baseret på denne beskrivelse: {prompt}"]}
            ])
            
            try:
                # Get raw text and find JSON bounds
                response_text = response.text.strip()
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx == -1 or end_idx == -1:
                    return jsonify({"error": "No valid JSON found in response"}), 500
                
                # Extract JSON and normalize newlines
                json_text = response_text[start_idx:end_idx + 1]
                json_text = json_text.replace('\n', ' ').replace('\r', '')
                
                try:
                    # Try parsing the normalized JSON
                    worksheet_data = json.loads(json_text)
                except json.JSONDecodeError:
                    # If that fails, try more aggressive cleaning
                    json_text = re.sub(r'\s+', ' ', json_text)  # Collapse whitespace
                    json_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)  # Quote keys
                    
                    try:
                        worksheet_data = json.loads(json_text)
                    except json.JSONDecodeError as e:
                        return jsonify({"error": f"Could not parse AI response as JSON: {str(e)}"}), 500
                
                # Validate structure
                if not isinstance(worksheet_data, dict) or 'worksheets' not in worksheet_data:
                    return jsonify({"error": "Invalid response format"}), 500
                
                if not isinstance(worksheet_data['worksheets'], list) or len(worksheet_data['worksheets']) != 2:
                    return jsonify({"error": "Expected exactly 2 worksheets"}), 500
                
                # Clean worksheet data
                for worksheet in worksheet_data['worksheets']:
                    for field in ['opgave_number', 'title', 'materials', 'sykl_del_type', 'sykl_del_a', 'bullet_points', 
                                'tips_1', 'tips_2', 'tips_3']:
                        # Ensure field exists
                        if field not in worksheet:
                            worksheet[field] = ''
                        
                        # Normalize text
                        worksheet[field] = normalize_text(worksheet[field])
                        
                        # Special handling for bullet points
                        if field == 'bullet_points' and worksheet[field]:
                            # Split on newlines (they're now actual newlines after normalize_text)
                            points = worksheet[field].split('\n')
                            # Clean and format each point
                            points = ['• ' + p.lstrip('•').strip() for p in points if p.strip()]
                            # Join with escaped newlines
                            worksheet[field] = '\\n'.join(points)
                
                return jsonify(worksheet_data)
                
            except Exception as e:
                return jsonify({"error": f"Error processing response: {str(e)}"}), 500
                
        except Exception as e:
            return jsonify({"error": f"Error generating content: {str(e)}"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    try:
        print("Starting server on port 3000")
        app.run(host='0.0.0.0', port=3000, debug=True)
    except OSError as e:
        print(f"Error starting server: {e}")
