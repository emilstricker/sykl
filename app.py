from flask import Flask, render_template, request, send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

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
        self.canv.setStrokeColor(colors.HexColor('#4A7C59'))
        self.canv.setLineWidth(1)
        self.canv.drawPath(p, fill=1, stroke=1)
        
        # Draw content
        y = self.height - self.padding
        
        # Draw the header first
        header = self.content_list[0]
        header.wrapOn(self.canv, self.width - 2*self.padding, y)
        header.drawOn(self.canv, self.padding, y - header.height)
        y -= header.height + 25  # Add extra space after the header
        
        # Draw the rest of the content
        for content in self.content_list[1:]:
            content.wrapOn(self.canv, self.width - 2*self.padding, y)
            content.drawOn(self.canv, self.padding, y - content.height)
            y -= content.height + 10
            
        self.canv.restoreState()

def create_pdf(opgave_number, title, materials, main_question, sykl_del_type, sykl_del_a, bullet_points, tips_1, tips_2, tips_3):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=40,
        leftMargin=40,
        rightMargin=40,
        bottomMargin=40
    )
    
    # Define colors
    sykl_green = colors.HexColor('#4A7C59')
    sykl_brown = colors.HexColor('#8B7355')
    sykl_beige = colors.HexColor('#F5F1E9')
    
    # Create custom styles
    styles = {
        'MainTitle': ParagraphStyle(
            'MainTitle',
            fontSize=28,
            textColor=sykl_green,
            spaceAfter=30,
            alignment=1,
            fontName='Helvetica-Bold'
        ),
        'SubTitle': ParagraphStyle(
            'SubTitle',
            fontSize=24,
            textColor=sykl_green,
            spaceAfter=20,
            alignment=1,
            fontName='Helvetica-Bold'
        ),
        'Heading': ParagraphStyle(
            'Heading',
            fontSize=16,
            textColor=sykl_brown,
            spaceBefore=15,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ),
        'BodyText': ParagraphStyle(
            'BodyText',
            fontSize=12,
            leading=16,
            spaceBefore=6,
            spaceAfter=6,
            fontName='Helvetica'
        ),
        'BulletPoint': ParagraphStyle(
            'BulletPoint',
            fontSize=12,
            leading=16,
            leftIndent=20,
            bulletIndent=10,
            fontName='Helvetica'
        ),
        'Tips': ParagraphStyle(
            'Tips',
            fontSize=12,
            leading=16,
            leftIndent=10,
            textColor=sykl_brown,
            fontName='Helvetica'
        ),
        'Footer': ParagraphStyle(
            'Footer',
            fontSize=8,
            textColor=colors.gray,
            alignment=1,
            fontName='Helvetica'
        )
    }
    
    # Build the document content
    story = []
    
    # Add logo
    logo_path = os.path.join(app.static_folder, 'images', 'sykl-logo-300x262.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=50, height=44)  # Slightly smaller logo
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 5))  # Reduced space after logo
    
    # Add title
    story.append(Paragraph(f"MATEMATIK • OPGAVE {opgave_number}", styles['MainTitle']))
    story.append(Paragraph(title, styles['SubTitle']))
    story.append(Spacer(1, 10))  # Reduced space after title
    
    # Add materials if provided
    if materials:
        story.append(Paragraph(f"<b>Materialer:</b> {materials}", styles['BodyText']))
        story.append(Spacer(1, 10))  # Reduced space after materials
    
    # Add main question
    story.append(Paragraph(main_question, styles['BodyText']))
    
    # Add space for graphics (reduced space)
    story.append(Spacer(1, 80))  # Reduced from 150
    
    # Add SYKL-DEL A or B
    story.append(Paragraph(f"<b>SYKL-DEL {sykl_del_type}:</b>", styles['Heading']))
    story.append(Paragraph(sykl_del_a, styles['BodyText']))
    
    # Add bullet points if provided
    if bullet_points:
        bullet_list = []
        for point in bullet_points.split('\n'):
            if point.strip():
                bullet_list.append(Paragraph(f"• {point.strip()}", styles['BulletPoint']))
        if bullet_list:
            story.append(Spacer(1, 5))  # Reduced space before bullets
            for bullet in bullet_list:
                story.append(bullet)
    
    story.append(Spacer(1, 20))  # Reduced space before MATEMA-TIPS
    
    # Add tips if provided in a rounded box
    if any([tips_1, tips_2, tips_3]):
        tips_content = []
        tips_content.append(Paragraph("<b>MATEMA-TIPS:</b>", styles['Heading']))
        if tips_1:
            tips_content.append(Paragraph(f"<b>{opgave_number}.1:</b> {tips_1}", styles['Tips']))
        if tips_2:
            tips_content.append(Paragraph(f"<b>{opgave_number}.2:</b> {tips_2}", styles['Tips']))
        if tips_3:
            tips_content.append(Paragraph(f"<b>{opgave_number}.3:</b> {tips_3}", styles['Tips']))
        
        # Calculate height based on content (reduced heights)
        box_height = 100  # Reduced base height
        if tips_1: box_height += 20
        if tips_2: box_height += 20
        if tips_3: box_height += 20
        
        story.append(RoundedBox(
            width=doc.width,
            height=box_height,
            content_list=tips_content,
            background_color=colors.HexColor('#F5F1E9').clone(alpha=0.5)
        ))
    
    # Build the PDF with a background color
    def add_background(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, A4[0], A4[1], fill=True)
        canvas.restoreState()
    
    doc.build(story, onFirstPage=add_background, onLaterPages=add_background)
    buffer.seek(0)
    return buffer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get form data
        opgave_number = request.form.get('opgave_number', '1')
        title = request.form.get('title', '')
        materials = request.form.get('materials', '')
        main_question = request.form.get('main_question', '')
        sykl_del_type = request.form.get('sykl_del_type', 'A')
        sykl_del_a = request.form.get('sykl_del_a', '')
        bullet_points = request.form.get('bullet_points', '')
        tips_1 = request.form.get('tips_1', '')
        tips_2 = request.form.get('tips_2', '')
        tips_3 = request.form.get('tips_3', '')

        # Generate PDF
        pdf = create_pdf(
            opgave_number,
            title,
            materials,
            main_question,
            sykl_del_type,
            sykl_del_a,
            bullet_points,
            tips_1,
            tips_2,
            tips_3
        )
        
        return send_file(
            pdf,
            download_name=f'sykl_opgave_{opgave_number}.pdf',
            mimetype='application/pdf'
        )

    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
