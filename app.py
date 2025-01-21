from flask import Flask, request, jsonify, send_file, render_template
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image, Table, TableStyle, ListFlowable, ListItem, Flowable
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from io import BytesIO
import os
import json
import re
import zipfile
import traceback
from google.cloud import translate
import google.generativeai as palm
from google.oauth2.credentials import Credentials
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Configure PaLM API
api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    raise Exception("API key not found in environment")
palm.configure(api_key=api_key)

# Create the Gemini model
generation_config = {
    "temperature": 0.9,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

model = palm.GenerativeModel(
    model_name="gemini-2.0-flash-exp",
    generation_config=generation_config,
)

# Initialize conversation with system prompt
conversation = [
    {"role": "system", "parts": ["""Du er en erfaren matematiklærer, der er ekspert i at skabe undersøgende og problembaserede matematikopgaver for 3.-4. klasse. 
    
Dine opgaver skal:
1. Være åbne og undersøgende
2. Opmuntre til forskellige løsningsstrategier
3. Relatere til elevernes hverdag
4. Fremme matematisk tænkning og ræsonnement
5. Invitere til samarbejde og diskussion
6. Have flere mulige løsninger eller løsningsveje

Format for hver opgave:
- Titel: Fængende og relevant
- Materialer: Konkrete materialer der understøtter undersøgelsen
- SYKL-DEL A: Den grundlæggende undersøgelse
- SYKL-DEL B: Udvidelse af undersøgelsen med flere variable eller højere kompleksitet
- Bullet points: Undersøgelsesspørgsmål (ikke ja/nej spørgsmål)
- Tips: Vejledende spørgsmål eller hints

Eksempel på god opgave:
Titel: "Byg den bedste papirflyver"
Materialer: "A4-papir, målebånd, stopur"
SYKL-DEL A: "I skal designe og teste papirflyvere. Undersøg hvordan forskellige designs påvirker hvor langt flyveren kan flyve."
Bullet points:
- "Hvordan påvirker vingernes form flyverens flugt?"
- "Hvilke mønstre ser I i jeres testresultater?"
- "Hvordan kan I dokumentere jeres undersøgelse?"
SYKL-DEL B: "Nu skal I optimere jeres design. Undersøg hvordan I kan få flyveren til at flyve både længst og være længst tid i luften."
Tips: "Prøv at måle både distance og tid. Kan I finde en sammenhæng? Hvordan kan I systematisk teste forskellige designs?"

Undgå:
- Lukkede opgaver med ét rigtigt svar
- Simple regneopgaver uden kontekst
- Opgaver uden relation til virkeligheden
- For styrende eller detaljerede instruktioner

Generer altid opgaver på dansk og brug et sprog der er passende for aldersgruppen."""]},
    {"role": "model", "parts": ["Jeg vil hjælpe med at generere undersøgende og problembaserede matematikopgaver der fremmer elevernes matematiske tænkning og kreativitet. Opgaverne vil være åbne, relevante og invitere til forskellige løsningsstrategier."]}
]

class RoundedBox(Flowable):
    def __init__(self, width, height=None, content="", padding=10, radius=10, background_color='#4A7C59'):
        Flowable.__init__(self)
        self.width = width
        self.content = content
        self.padding = padding
        self.radius = radius
        self.background_color = background_color
        
        # Calculate height based on content if not specified
        if height is None:
            # Rough estimation of height based on content length and width
            content_lines = len(content) / (width / 10)  # Approximate characters per line
            self.height = max(50, content_lines * 20 + 2 * padding)
        else:
            self.height = height
    
    def draw(self):
        # Draw rounded rectangle
        self.canv.setFillColor(self.background_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1)
        
        # Add text
        self.canv.setFillColor('white')
        self.canv.setFont('ArialRoundedMTBold', 14)
        
        # Draw text with padding
        text_object = self.canv.beginText(self.padding, self.height - self.padding - 14)
        for line in self.content.split('\n'):
            text_object.textLine(line.strip())
        self.canv.drawText(text_object)

def get_font_name():
    """Get the font name to use, with fallback to Helvetica"""
    try:
        # Try to use the font to see if it's registered
        pdfmetrics.getFont('ArialRoundedMTBold')
        return 'ArialRoundedMTBold'
    except:
        return 'Helvetica-Bold'

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
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=30,
        bottomMargin=30
    )
    
    # Define colors
    sykl_green = '#4A7C59'  # Dark green for headers
    
    # Register Arial Rounded MT Bold font if available
    font_path = os.path.join('static', 'fonts', 'arialroundedmtbold.ttf')
    try:
        pdfmetrics.registerFont(TTFont('ArialRoundedMTBold', font_path))
    except:
        print("Warning: Could not load Arial Rounded MT Bold font, falling back to Helvetica")
    
    # Get the font name to use
    display_font = get_font_name()
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Header style
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='black',
        spaceAfter=10,
        alignment=1,  # Center alignment
        fontName=display_font
    )
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=sykl_green,
        spaceAfter=15,
        fontName=display_font
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=sykl_green,
        spaceBefore=10,
        spaceAfter=5,
        fontName=display_font
    )
    
    # Normal text style
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=5,
        leading=18,
        fontName='Helvetica'
    )
    
    # Tips text style
    tips_style = ParagraphStyle(
        'CustomTips',
        parent=styles['Normal'],
        fontSize=14,
        textColor='white',
        spaceAfter=3,
        leading=16,
        fontName=display_font
    )
    
    story = []
    
    # Add logo
    logo_path = os.path.join('static', 'images', 'sykl-logo-300x262.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=60, height=52.4)  # Increased size
        story.append(logo)
        story.append(Spacer(1, 10))
    
    # Header
    header_text = 'MATEMATIK<br/><font color="%s" size="20">OPGAVEARK</font>' % sykl_green
    story.append(Paragraph(header_text, header_style))
    story.append(Spacer(1, 10))
    
    # Title
    story.append(Paragraph(worksheet_data['title'].upper(), title_style))
    
    # Materials
    story.append(Paragraph(f"<b>Materialer:</b> {worksheet_data['materials']}", normal_style))
    
    # SYKL-DEL section
    story.append(Paragraph(f"SYKL-DEL {worksheet_data['sykl_del_type']}:", subtitle_style))
    
    # Main task description
    description = worksheet_data['sykl_del_a'].replace('\\n', '<br/>')
    story.append(Paragraph(description, normal_style))
    
    # Bullet points
    if worksheet_data['bullet_points']:
        bullet_points = split_bullet_points(worksheet_data['bullet_points'])
        if bullet_points:
            items = [ListItem(Paragraph(point, normal_style)) for point in bullet_points]
            story.append(ListFlowable(
                items,
                bulletType='bullet',
                start='•',
                bulletFontSize=14,
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
                ('TEXTCOLOR', (0, 0), (-1, -1), 'white'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), display_font),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ])
            
            # Create the table with tips
            tips_table = Table([[tip] for tip in tips_box], colWidths=[doc.width * 0.8])
            tips_table.setStyle(table_style)
            
            # Add some space before the tips box
            story.append(Spacer(1, 10))
            story.append(tips_table)
    
    # Build PDF
    doc.build(story)
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

def get_credentials():
    """Get Google Cloud credentials from environment variable."""
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'gen-lang-client-0129661352')
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise Exception("API key not found in environment")
    return project_id, api_key

def get_translate_client():
    """Get translation client with API key authentication."""
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise Exception("API key not found in environment")
    
    credentials = Credentials(token=api_key)
    client = translate.TranslationServiceClient(credentials=credentials)
    return client, api_key

def translate_text(text, target_language="da"):
    """Translate text using API key."""
    try:
        client, api_key = get_translate_client()
        project_id = "gen-lang-client-0129661352"
        location = "global"
        parent = f"projects/{project_id}/locations/{location}"
        
        response = client.translate_text(
            request={
                "contents": [text],
                "target_language_code": target_language,
                "source_language_code": "en",
                "parent": parent,
                "mime_type": "text/plain"
            }
        )
        
        return response.translations[0].translated_text
    except Exception as e:
        print(f"Translation error: {str(e)}")
        raise Exception(f"Translation error: {str(e)}")

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
    """Generate a worksheet based on the prompt."""
    if request.method == 'POST':
        prompt = request.json.get('prompt')
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        try:
            # Add the subject to the conversation
            full_conversation = conversation + [
                {"role": "user", "parts": [f"Generer en undersøgende matematikopgave om emnet: {prompt}"]}
            ]
            
            response = model.generate_content(full_conversation)
            response_text = response.text
            
            # Extract title
            title_match = re.search(r'Titel:\s*"([^"]+)"', response_text)
            title = title_match.group(1) if title_match else "Matematikopgave"
            
            # Extract materials
            materials_match = re.search(r'Materialer:\s*"([^"]+)"', response_text)
            materials = materials_match.group(1) if materials_match else ""
            
            # Extract SYKL-DEL A
            sykl_a_match = re.search(r'SYKL-DEL A:\s*"([^"]+)"', response_text)
            sykl_del_a = sykl_a_match.group(1) if sykl_a_match else ""
            
            # Extract bullet points
            bullet_points_text = ""
            bullet_points_match = re.search(r'Bullet points:(.*?)(?=SYKL-DEL B|Tips|$)', response_text, re.DOTALL)
            if bullet_points_match:
                points = re.findall(r'-\s*"([^"]+)"', bullet_points_match.group(1))
                bullet_points_text = "• " + "\n• ".join(points) if points else ""
            
            # Extract tips
            tips_match = re.search(r'Tips:\s*"([^"]+)"', response_text)
            tips = tips_match.group(1) if tips_match else ""
            tips_list = [tip.strip() for tip in tips.split('?') if tip.strip()]
            
            # Create worksheet data
            worksheet_data = {
                "title": title,
                "materials": materials,
                "sykl_del_type": "A",
                "sykl_del_a": sykl_del_a,
                "bullet_points": bullet_points_text,
                "tips_1": (tips_list[0] + "?") if len(tips_list) > 0 else "",
                "tips_2": (tips_list[1] + "?") if len(tips_list) > 1 else "",
                "tips_3": (tips_list[2] + "?") if len(tips_list) > 2 else ""
            }
            
            # Generate PDF
            try:
                pdf_buffer = create_pdf(worksheet_data)
                return send_file(
                    pdf_buffer,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f"sykl_opgave_{title.lower().replace(' ', '_')}.pdf"
                )
            except Exception as e:
                print(f"Error generating PDF: {str(e)}")
                return jsonify({"error": f"Error generating PDF: {str(e)}"}), 500
                
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            return jsonify({"error": f"Error generating content: {str(e)}"}), 500

    return jsonify({"error": "Invalid request method"}), 405

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        
        # Configure PaLM
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise Exception("API key not found in environment")
        palm.configure(api_key=api_key)
        
        # Generate content using PaLM
        completion = palm.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_output_tokens=800,
        )
        
        if completion.result:
            # Translate the generated content
            translated_text = translate_text(completion.result)
            return jsonify({"content": translated_text})
        else:
            return jsonify({"error": "No content generated"}), 400
            
    except Exception as e:
        print(f"Error generating content: {str(e)}")
        return jsonify({"error": f"Error generating content: {str(e)}"}), 500

if __name__ == '__main__':
    try:
        print("Starting server on port 3000")
        app.run(host='0.0.0.0', port=3000, debug=True)
    except OSError as e:
        print(f"Error starting server: {e}")
