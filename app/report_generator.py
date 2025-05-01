from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch, cm
import io
import json
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        # Add custom styles with unique names
        self.styles.add(ParagraphStyle(
            name='ReportTitle',  # Changed from 'Title' to 'ReportTitle'
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        self.styles.add(ParagraphStyle(
            name='ReportSubtitle',  # Changed from 'Subtitle' to 'ReportSubtitle'
            parent=self.styles['Heading2'],
            fontSize=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='ReportSectionTitle',  # Changed from 'SectionTitle' to 'ReportSectionTitle'
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2980b9'),
            spaceAfter=10
        ))
        self.styles.add(ParagraphStyle(
            name='ReportNormal',  # Changed from 'Normal' to 'ReportNormal'
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=5,
            spaceAfter=5
        ))
        self.styles.add(ParagraphStyle(
            name='ReportBulletPoint',  # Changed from 'BulletPoint' to 'ReportBulletPoint'
            parent=self.styles['Normal'],
            fontSize=11,
            leftIndent=20,
            spaceBefore=2,
            spaceAfter=2
        ))
        self.styles.add(ParagraphStyle(
            name='ExecutivePrelude',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Oblique',
            textColor=colors.HexColor('#34495e'),
            spaceBefore=10,
            spaceAfter=15
        ))

    def _add_cover_page(self, doc_elements, business_name, profession_name, owner_name):
        """Add a professional cover page to the report"""
        # Logo path - adjust based on your project structure
        logo_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')
        if os.path.exists(logo_path):
            doc_elements.append(Image(logo_path, width=2*inch, height=1*inch))
        
        # Add some space
        doc_elements.append(Spacer(1, 1*inch))
        
        # Title
        doc_elements.append(Paragraph(f"BUSINESS TRANSFORMATION BLUEPRINT™", self.styles['ReportTitle']))
        doc_elements.append(Paragraph(f"AI-Powered Premium Business Audit for {profession_name}", self.styles['ReportSubtitle']))
        doc_elements.append(Paragraph("A Strategic Intelligence Report with Intelligent Execution Implementation", self.styles['ReportNormal']))
        
        # Add some space
        doc_elements.append(Spacer(1, 0.5*inch))
        
        # Date
        current_date = datetime.now().strftime("%B %d, %Y")
        doc_elements.append(Paragraph(f"Generated on: {current_date}", self.styles['ReportNormal']))
        
        # Add some space
        doc_elements.append(Spacer(1, 1*inch))
        
        # Executive prelude
        prelude_text = f"""For the attention of: {owner_name}, {business_name}
        
In the competitive landscape of {profession_name.lower().replace('excellence', '')}, your business exists in a state of profound potential. This is not merely an analysis, but a transformation manuscript. We have examined your business through the lens of advanced intelligence, identifying precisely where your expertise can be multiplied, your time reclaimed, and your client impact magnified.

The following pages contain not abstract concepts, but precise coordinates for your evolution from respected business owner to an industry authority. Within these insights lies the difference between modest growth and profound transformation—between serving clients through manual effort and becoming a defining force through intelligent automation.

Let us begin.
— Business Intelligence Core"""
        doc_elements.append(Paragraph(prelude_text, self.styles['ExecutivePrelude']))
        
        # Page break
        doc_elements.append(Spacer(1, 1*inch))
        
    def _add_business_basics(self, doc_elements, answers, profession):
        """Add business basics section"""
        doc_elements.append(Paragraph("I. BUSINESS INTELLIGENCE OVERVIEW", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Find Business Basics section in the answers
        business_basics = {}
        for section in answers:
            if section.get("title", "").lower() == "business basics":
                business_basics = section.get("answers", {})
                break
        
        if not business_basics:
            doc_elements.append(Paragraph("No business basics information available.", self.styles['ReportNormal']))
            return
        
        # Create a table to display business information
        data = []
        for question, answer in business_basics.items():
            if answer and not question.startswith("_"):
                data.append([Paragraph(question, self.styles['ReportNormal']), 
                            Paragraph(answer, self.styles['ReportNormal'])])
        
        if data:
            table = Table(data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            doc_elements.append(table)
        
        doc_elements.append(Spacer(1, 0.2*inch))
        
    def _add_revenue_metrics(self, doc_elements, answers):
        """Add revenue and operational metrics section"""
        doc_elements.append(Paragraph("II. REVENUE & OPERATIONAL METRICS", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Find Revenue section in the answers
        revenue_metrics = {}
        for section in answers:
            if "revenue" in section.get("title", "").lower():
                revenue_metrics = section.get("answers", {})
                break
        
        if not revenue_metrics:
            doc_elements.append(Paragraph("No revenue metrics information available.", self.styles['ReportNormal']))
            return
        
        # Add paragraph about revenue insights
        revenue_text = """Based on the financial data provided, we've analyzed your revenue streams and operational metrics to identify optimization opportunities:"""
        doc_elements.append(Paragraph(revenue_text, self.styles['ReportNormal']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Create bullet points for each revenue insight
        for question, answer in revenue_metrics.items():
            if answer and not question.startswith("_"):
                insight_text = f"• <b>{question}:</b> {answer}"
                doc_elements.append(Paragraph(insight_text, self.styles['ReportBulletPoint']))
        
        # Add growth potential paragraph
        growth_text = """<b>Growth Potential:</b> Based on these metrics, we've identified several opportunities to optimize your revenue streams and operational efficiency. The implementation of automated systems could potentially increase your revenue by 25-40% while reducing operational overhead."""
        doc_elements.append(Spacer(1, 0.1*inch))
        doc_elements.append(Paragraph(growth_text, self.styles['ReportNormal']))
        
        doc_elements.append(Spacer(1, 0.2*inch))
        
    def _add_challenges_section(self, doc_elements, answers):
        """Add operational challenges section"""
        doc_elements.append(Paragraph("III. OPERATIONAL CHALLENGES & SOLUTIONS", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Find Challenges section in the answers
        challenges = {}
        for section in answers:
            if "challenge" in section.get("title", "").lower() or "operation" in section.get("title", "").lower():
                challenges = section.get("answers", {})
                break
        
        if not challenges:
            doc_elements.append(Paragraph("No operational challenges information available.", self.styles['ReportNormal']))
            return
        
        # Add introduction paragraph
        intro_text = """We've identified the following operational challenges in your business and developed targeted solutions to address each one:"""
        doc_elements.append(Paragraph(intro_text, self.styles['ReportNormal']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Create a table for challenges and solutions
        data = [["Challenge", "AI-Powered Solution"]]
        
        for question, answer in challenges.items():
            if answer and not question.startswith("_"):
                # Generate a custom solution for each challenge
                solution = self._generate_solution_for_challenge(question, answer)
                data.append([
                    Paragraph(f"{question}: {answer}", self.styles['ReportNormal']),
                    Paragraph(solution, self.styles['ReportNormal'])
                ])
        
        if len(data) > 1:
            table = Table(data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2980b9')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            doc_elements.append(table)
        
        doc_elements.append(Spacer(1, 0.2*inch))
        
    def _generate_solution_for_challenge(self, question, answer):
        """Generate a custom solution based on the challenge"""
        # This is a simple implementation - in a production system, you might use
        # more sophisticated logic or even an AI model to generate tailored solutions
        if "time" in question.lower() or "hours" in question.lower():
            return "Implement an AI-powered automation system to reduce time spent on this task by 70-80%, freeing you to focus on high-value activities."
        elif "bottleneck" in question.lower():
            return "Our process optimization framework identifies and eliminates bottlenecks through intelligent workflow redesign and targeted automation."
        elif "management" in question.lower() or "handling" in question.lower():
            return "Deploy a custom management automation system that handles routine tasks while maintaining personal touch for important client interactions."
        else:
            return "Deploy custom AI solutions to streamline this process, reducing manual effort while improving outcomes."
    
    def _add_market_section(self, doc_elements, answers):
        """Add market and competitor section"""
        doc_elements.append(Paragraph("IV. MARKET & COMPETITIVE POSITIONING", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Find Market section in the answers
        market_data = {}
        for section in answers:
            if "market" in section.get("title", "").lower() or "competitor" in section.get("title", "").lower():
                market_data = section.get("answers", {})
                break
        
        if not market_data:
            doc_elements.append(Paragraph("No market information available.", self.styles['ReportNormal']))
            return
        
        # Add market positioning paragraph
        market_text = """Based on your competitive landscape and market position, we've identified strategic opportunities to differentiate your business:"""
        doc_elements.append(Paragraph(market_text, self.styles['ReportNormal']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Extract competitor information
        competitors = None
        unique_selling = None
        pricing = None
        
        for question, answer in market_data.items():
            if answer and "competitor" in question.lower():
                competitors = answer
            elif answer and ("unique" in question.lower() or "different" in question.lower()):
                unique_selling = answer
            elif answer and "pricing" in question.lower():
                pricing = answer
        
        # Add competitor analysis
        if competitors:
            doc_elements.append(Paragraph("<b>Competitor Analysis:</b>", self.styles['ReportNormal']))
            doc_elements.append(Paragraph(f"• {competitors}", self.styles['ReportBulletPoint']))
            doc_elements.append(Spacer(1, 0.1*inch))
        
        # Add differentiation strategy
        if unique_selling:
            doc_elements.append(Paragraph("<b>Your Unique Advantage:</b>", self.styles['ReportNormal']))
            doc_elements.append(Paragraph(f"• {unique_selling}", self.styles['ReportBulletPoint']))
            
            # Add strategic recommendation
            strategy_text = """<b>Strategic Opportunity:</b> Amplify your unique strengths through targeted messaging and service design. We recommend developing an automated system that consistently delivers on your unique value proposition while scaling your reach."""
            doc_elements.append(Paragraph(strategy_text, self.styles['ReportNormal']))
            doc_elements.append(Spacer(1, 0.1*inch))
        
        # Add pricing strategy
        if pricing:
            doc_elements.append(Paragraph("<b>Pricing Position:</b>", self.styles['ReportNormal']))
            doc_elements.append(Paragraph(f"• Current positioning: {pricing}", self.styles['ReportBulletPoint']))
            
            # Add pricing recommendation
            if "premium" in pricing.lower():
                price_text = """<b>Pricing Strategy:</b> Your premium positioning allows for implementation of value-based offerings. We recommend developing tiered service packages with automated delivery to maximize revenue while maintaining premium positioning."""
            elif "average" in pricing.lower():
                price_text = """<b>Pricing Strategy:</b> Your average pricing presents an opportunity to develop premium service tiers with automated delivery, potentially increasing average transaction value by 30-40%."""
            else:
                price_text = """<b>Pricing Strategy:</b> We recommend developing automated service components that can be delivered at scale, allowing for introduction of higher-tier offerings while maintaining your accessible pricing for entry-level services."""
                
            doc_elements.append(Paragraph(price_text, self.styles['ReportNormal']))
        
        doc_elements.append(Spacer(1, 0.2*inch))
        
    def _add_tech_section(self, doc_elements, answers):
        """Add technology and automation section"""
        doc_elements.append(Paragraph("V. TECHNOLOGY & AUTOMATION POTENTIAL", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Find Tech section in the answers
        tech_data = {}
        for section in answers:
            if "tech" in section.get("title", "").lower() or "automation" in section.get("title", "").lower():
                tech_data = section.get("answers", {})
                break
        
        if not tech_data:
            doc_elements.append(Paragraph("No technology information available.", self.styles['ReportNormal']))
            return
        
        # Add technology assessment paragraph
        tech_text = """Based on your current technology stack and openness to AI/automation, we've identified the following opportunities:"""
        doc_elements.append(Paragraph(tech_text, self.styles['ReportNormal']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Create bullet points for technology recommendations
        systems_used = None
        pain_points = None
        openness_to_ai = None
        
        for question, answer in tech_data.items():
            if answer:
                if "systems" in question.lower() or "tools" in question.lower():
                    systems_used = answer
                elif "pain points" in question.lower() or "integrated" in question.lower():
                    pain_points = answer
                elif "ai" in question.lower() or "automation" in question.lower():
                    openness_to_ai = answer
        
        # Add current technology assessment
        if systems_used:
            doc_elements.append(Paragraph("<b>Current Technology Assessment:</b>", self.styles['ReportNormal']))
            doc_elements.append(Paragraph(f"• {systems_used}", self.styles['ReportBulletPoint']))
            doc_elements.append(Spacer(1, 0.1*inch))
        
        # Add integration challenges
        if pain_points:
            doc_elements.append(Paragraph("<b>Integration Challenges:</b>", self.styles['ReportNormal']))
            doc_elements.append(Paragraph(f"• {pain_points}", self.styles['ReportBulletPoint']))
            doc_elements.append(Spacer(1, 0.1*inch))
        
        # Add automation roadmap
        doc_elements.append(Paragraph("<b>AI Automation Roadmap:</b>", self.styles['ReportNormal']))
        
        # Add customized automation recommendations
        doc_elements.append(Paragraph("• <b>Core Business Generator™:</b> Automated system for creating customized client deliverables, reducing production time by 80%", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• <b>Client Engagement Accelerator™:</b> Automated client follow-up and relationship management system", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• <b>Content Creation Engine™:</b> AI-powered content generation for marketing and client communications", self.styles['ReportBulletPoint']))
        
        # Add implementation note based on openness to AI
        if openness_to_ai and ("yes" in openness_to_ai.lower() or "open" in openness_to_ai.lower()):
            implementation = """<b>Implementation Note:</b> Based on your openness to AI technologies, we recommend a phased implementation starting with the Core Business Generator™ to establish immediate time savings, followed by the Client Engagement Accelerator™ and Content Creation Engine™."""
        else:
            implementation = """<b>Implementation Note:</b> We recommend a gradual approach to implementation, starting with the Core Business Generator™ to establish value and build confidence, followed by other systems as comfort with automation increases."""
            
        doc_elements.append(Spacer(1, 0.1*inch))
        doc_elements.append(Paragraph(implementation, self.styles['ReportNormal']))
        
        doc_elements.append(Spacer(1, 0.2*inch))
        
    def _add_transformation_plan(self, doc_elements, profession_name):
        """Add transformation plan section"""
        doc_elements.append(Paragraph("VI. 90-DAY TRANSFORMATION PLAN", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Add introduction paragraph
        intro_text = f"""Based on our comprehensive analysis of your {profession_name.lower().replace('excellence', '').strip()} business, we've developed a 90-day transformation plan to implement AI-powered systems that will dramatically improve your efficiency and growth potential."""
        doc_elements.append(Paragraph(intro_text, self.styles['ReportNormal']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Phase 1: First 30 days
        doc_elements.append(Paragraph("<b>Phase 1 (Days 1-30): Core System Implementation</b>", self.styles['ReportNormal']))
        doc_elements.append(Paragraph("• Week 1: Core Business Generator™ implementation and training", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• Week 2: Process assessment and workflow mapping", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• Weeks 3-4: Initial automation of key processes", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("<b>Expected Outcomes:</b> 10+ hours weekly time reclamation, 30% improvement in delivery efficiency", self.styles['ReportBulletPoint']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Phase 2: Days 31-60
        doc_elements.append(Paragraph("<b>Phase 2 (Days 31-60): Client Experience Enhancement</b>", self.styles['ReportNormal']))
        doc_elements.append(Paragraph("• Week 5: Client Engagement Accelerator™ implementation", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• Week 6: Automated follow-up sequences and client journey mapping", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• Weeks 7-8: Client feedback integration and system optimization", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("<b>Expected Outcomes:</b> 65% reduction in client management time, improved retention and satisfaction", self.styles['ReportBulletPoint']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Phase 3: Days 61-90
        doc_elements.append(Paragraph("<b>Phase 3 (Days 61-90): Growth Acceleration</b>", self.styles['ReportNormal']))
        doc_elements.append(Paragraph("• Week 9: Content Creation Engine™ implementation", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• Week 10: Automated marketing system development", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("• Weeks 11-12: Business intelligence dashboard implementation and team training", self.styles['ReportBulletPoint']))
        doc_elements.append(Paragraph("<b>Expected Outcomes:</b> 2 new revenue streams, 50% increase in lead generation, comprehensive business insights", self.styles['ReportBulletPoint']))
        
        doc_elements.append(Spacer(1, 0.2*inch))
        
    def _add_conclusion(self, doc_elements, business_name, profession_name):
        """Add conclusion section"""
        doc_elements.append(Paragraph("CLOSING REFLECTION", self.styles['ReportSectionTitle']))
        doc_elements.append(Spacer(1, 0.1*inch))
        
        # Add conclusion paragraph
        conclusion_text = f"""The insights contained within this document represent not merely what {business_name} is, but what it is becoming. You stand at the threshold of a new {profession_name.lower().replace('excellence', '').strip()} business paradigm—one where your expertise and artificial intelligence create a business that is simultaneously more impactful and more efficient.

Each implementation builds upon a foundation of excellence, creating a practice that becomes more valuable, more client-focused, and more profitable with each passing day.

Imagine waking up to find your deliverables perfectly designed, your client progress automatically tracked, and your marketing consistently building your brand—all while you focus solely on the high-value activities that fulfill you. This isn't just automation; it's your business vision and potential unlocked.

Your journey toward becoming a defining voice in your industry has already begun. The question now is not whether to proceed, but how quickly you wish to evolve.

With precision and purpose,

— Business Intelligence Core

Business Transformation Blueprint™
Precision. Intelligence. Evolution."""
        doc_elements.append(Paragraph(conclusion_text, self.styles['ReportNormal']))
        
    def generate_report(self, user_id, business_name, owner_name, profession_name, answers):
        """Generate a PDF report based on the user's answers"""
        logger.info(f"Generating report for user {user_id}, business: {business_name}")
        
        try:
            # Create a BytesIO buffer to receive the PDF data
            buffer = io.BytesIO()
            
            # Create the PDF document using ReportLab
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=A4,
                rightMargin=1*inch,
                leftMargin=1*inch,
                topMargin=1*inch,
                bottomMargin=1*inch
            )
            
            # Container for the elements to be added to the document
            elements = []
            
            # Add cover page
            self._add_cover_page(elements, business_name, profession_name, owner_name)
            
            # Add business basics section
            self._add_business_basics(elements, answers, profession_name)
            
            # Add revenue and metrics section
            self._add_revenue_metrics(elements, answers)
            
            # Add operational challenges section
            self._add_challenges_section(elements, answers)
            
            # Add market and competitor section
            self._add_market_section(elements, answers)
            
            # Add technology section
            self._add_tech_section(elements, answers)
            
            # Add transformation plan
            self._add_transformation_plan(elements, profession_name)
            
            # Add conclusion
            self._add_conclusion(elements, business_name, profession_name)
            
            # Build the PDF document
            doc.build(elements)
            
            # Get the PDF data from the BytesIO buffer
            pdf_data = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Report generated successfully for user {user_id}")
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise e

# Create an instance of the report generator
report_generator = ReportGenerator()

def generate_business_report(user_id, business_name, owner_name, profession_name, answers):
    """Generate a business audit report for the user"""
    return report_generator.generate_report(user_id, business_name, owner_name, profession_name, answers)