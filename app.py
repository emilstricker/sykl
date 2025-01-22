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

# Conversation history to guide the model
conversation_history = [
    {"role": "user", "parts": ["""You are a Danish elementary school math teacher who creates engaging, open-ended math problems that promote problem-solving skills and mathematical thinking. Your worksheets should:

1. Focus on real-world scenarios that students can relate to
2. Encourage multiple solution strategies
3. Ask students to explain their thinking
4. Include opportunities for creative problem-solving
5. Promote mathematical discussions
6. Allow for different skill levels
7. Integrate visual thinking and drawing

Please generate a worksheet in this format:
{
    "title": "Title of the worksheet",
    "materials": "List of required materials",
    "sykl_del_type": "A or B",
    "sykl_del_a": "Main task description",
    "bullet_points": "Additional questions or tasks",
    "tips": "Helpful tips for solving the problem"
}

Make sure the content is age-appropriate for grades 3-4 (9-10 years old)."""]},
    
    {"role": "model", "parts": ["I'll help create engaging, open-ended math worksheets that promote problem-solving and mathematical thinking. I'll ensure they:

1. Use authentic contexts that 9-10 year olds can relate to
2. Encourage exploration and multiple solution paths
3. Ask 'how' and 'why' questions to promote mathematical reasoning
4. Include creative elements like drawing and designing
5. Foster group discussions and sharing of strategies
6. Allow for differentiation through low floor, high ceiling tasks
7. Integrate visual representations and spatial thinking

I'll format the worksheets as requested, with clear materials, tasks, and helpful tips."]},

    {"role": "user", "parts": ["Great! Please generate a worksheet that follows these principles. Remember to make it engaging and open-ended, while still being appropriate for 3rd-4th grade."]},
    
    {"role": "model", "parts": ["""Here's an example of how I'll structure open-ended math problems:

{
    "title": "Design en Pizza Restaurant",
    "materials": "Papir, blyant, lineal, farver",
    "sykl_del_type": "A",
    "sykl_del_a": "Du skal hjælpe med at designe menuen til en ny pizza restaurant! Restauranten vil gerne have forskellige størrelser af pizzaer: lille (20 cm), mellem (30 cm) og stor (40 cm). Undersøg og sammenlign de forskellige pizzastørrelser.",
    "bullet_points": "• Tegn de forskellige pizzastørrelser på dit papir. Hvordan kan du sammenligne dem?\n• Hvor meget større er en stor pizza end en lille pizza? Find på forskellige måder at vise det.\n• Hvis en mellem pizza koster 80 kr., hvad synes du så en lille og en stor pizza skal koste? Forklar din tankegang.\n• Hvordan kan du vise, at din prissætning er retfærdig?\n• Bonus: Design din egen specialpizza og beregn en fair pris for den.",
    "tips": "Tænk på arealet af cirklerne • Brug tegninger til at vise dine sammenligninger • Der er mange rigtige måder at løse opgaven på • Del dine ideer med en klassekammerat"
}

This problem:
1. Uses a familiar context (pizzas)
2. Involves multiple math concepts (geometry, measurement, proportional reasoning)
3. Allows for different solution strategies
4. Encourages visual thinking and creativity
5. Promotes discussion and justification
6. Can be approached at different levels
7. Has real-world applications"""]},

    {"role": "user", "parts": ["Perfect! Now generate another worksheet following the same principles."]}
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
def generate():
    """Generate a worksheet based on the provided prompt."""
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        try:
            response = model.generate_content(conversation_history + [
                {"role": "user", "parts": [f"Generer et opgaveark baseret på denne beskrivelse: {prompt}"]}
            ])
            
            # Parse the response
            try:
                worksheet_data = json.loads(response.text)
                
                # Generate PDF
                pdf_buffer = create_pdf(worksheet_data)
                
                # Save worksheet data
                worksheet_number = len(os.listdir('opgaver')) + 1
                worksheet_filename = f'opgave{worksheet_number}.json'
                
                with open(os.path.join('opgaver', worksheet_filename), 'w', encoding='utf-8') as f:
                    json.dump(worksheet_data, f, ensure_ascii=False, indent=4)
                
                # Return PDF file
                return send_file(
                    pdf_buffer,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=f'worksheet_{worksheet_number}.pdf'
                )
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {str(e)}")
                print(f"Response text: {response.text}")
                return jsonify({"error": f"Error parsing response: {str(e)}"}), 500
                
        except Exception as e:
            print(f"Generation error: {str(e)}")
            traceback.print_exc()
            return jsonify({"error": f"Error generating content: {str(e)}"}), 500

@app.route('/generate', methods=['POST'])
def generate_worksheet():
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
