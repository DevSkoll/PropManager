"""
PDF generation service for eDocuments.

Uses WeasyPrint to generate signed PDF documents with embedded signatures.
"""

import io
import logging
from datetime import datetime

import markdown
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

from ..markdown_parser import replace_tags_with_html
from ..variables import TemplateVariableResolver

logger = logging.getLogger(__name__)


class EDocumentPDFGenerator:
    """
    Generates PDF versions of signed eDocuments.

    Uses WeasyPrint to convert rendered HTML to PDF format with
    embedded signatures and audit trail.
    """

    def __init__(self, edocument):
        """Initialize with an EDocument instance."""
        self.edocument = edocument

    def generate(self) -> bytes:
        """
        Generate PDF content for the eDocument.

        Returns:
            bytes: PDF file content
        """
        # Render the document content
        rendered_html = self._render_content()

        # Build the full HTML document
        full_html = self._build_html_document(rendered_html)

        # Convert to PDF using WeasyPrint
        pdf_bytes = self._html_to_pdf(full_html)

        return pdf_bytes

    def generate_and_save(self) -> bool:
        """
        Generate PDF and save to the eDocument's final_pdf field.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            pdf_bytes = self.generate()

            # Create a filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"edoc_{self.edocument.pk}_{timestamp}.pdf"

            # Save to model
            self.edocument.final_pdf.save(
                filename,
                ContentFile(pdf_bytes),
                save=True
            )

            logger.info(f"Generated PDF for eDocument {self.edocument.pk}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF for eDocument {self.edocument.pk}: {e}")
            return False

    def _render_content(self) -> str:
        """Render the document content with variables and signatures."""
        # Substitute variables
        if self.edocument.lease:
            resolver = TemplateVariableResolver(
                lease=self.edocument.lease,
                landlord_user=self.edocument.created_by,
            )
            content = resolver.substitute(self.edocument.content)
        else:
            content = self.edocument.content

        # Convert markdown to HTML
        html = markdown.markdown(
            content,
            extensions=["tables", "fenced_code", "nl2br"]
        )

        # Replace signature tags with actual signatures
        signed_blocks = {
            block.block_order: block.image
            for block in self.edocument.signature_blocks.filter(signed_at__isnull=False)
        }
        html = replace_tags_with_html(html, signed_blocks=signed_blocks)

        return html

    def _build_html_document(self, body_html: str) -> str:
        """Build a complete HTML document for PDF generation."""
        # Get signer information for the audit trail
        signers = []
        for signer in self.edocument.signers.filter(signed_at__isnull=False):
            signers.append({
                "name": signer.name,
                "role": signer.get_role_display(),
                "signed_at": signer.signed_at,
                "ip_address": signer.ip_address or "N/A",
            })

        context = {
            "edocument": self.edocument,
            "body_html": body_html,
            "signers": signers,
            "generated_at": datetime.now(),
        }

        # Try to use a template, fall back to inline HTML
        try:
            return render_to_string("documents/pdf/edocument.html", context)
        except Exception:
            return self._build_inline_html(context)

    def _build_inline_html(self, context: dict) -> str:
        """Build HTML inline if template is not available."""
        signers_html = ""
        for signer in context["signers"]:
            signers_html += f"""
            <tr>
                <td>{signer['name']}</td>
                <td>{signer['role']}</td>
                <td>{signer['signed_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                <td>{signer['ip_address']}</td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{context['edocument'].title}</title>
            <style>
                @page {{
                    size: letter;
                    margin: 1in;
                }}
                body {{
                    font-family: 'Times New Roman', Times, serif;
                    font-size: 12pt;
                    line-height: 1.5;
                    color: #000;
                }}
                h1 {{
                    font-size: 18pt;
                    text-align: center;
                    margin-bottom: 1em;
                }}
                h2 {{
                    font-size: 14pt;
                    border-bottom: 1px solid #000;
                    padding-bottom: 0.25em;
                    margin-top: 1.5em;
                }}
                h3 {{
                    font-size: 12pt;
                    margin-top: 1em;
                }}
                p {{
                    margin: 0.5em 0;
                    text-align: justify;
                }}
                .signature-block {{
                    display: inline-block;
                    border: 1px solid #ccc;
                    padding: 10px;
                    margin: 10px 0;
                    background: #f9f9f9;
                    text-align: center;
                }}
                .signature-block.signed {{
                    background: #e8f5e9;
                    border-color: #4caf50;
                }}
                .signature-image {{
                    max-height: 60px;
                    max-width: 200px;
                }}
                .signature-label {{
                    display: block;
                    font-size: 10pt;
                    color: #666;
                    margin-top: 5px;
                }}
                .audit-section {{
                    margin-top: 2em;
                    padding-top: 1em;
                    border-top: 2px solid #000;
                    page-break-inside: avoid;
                }}
                .audit-section h2 {{
                    font-size: 12pt;
                    border: none;
                    margin-bottom: 0.5em;
                }}
                .audit-table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 10pt;
                }}
                .audit-table th, .audit-table td {{
                    border: 1px solid #ccc;
                    padding: 5px 10px;
                    text-align: left;
                }}
                .audit-table th {{
                    background: #f0f0f0;
                }}
                .footer {{
                    margin-top: 1em;
                    font-size: 9pt;
                    color: #666;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <h1>{context['edocument'].title}</h1>

            <div class="document-body">
                {context['body_html']}
            </div>

            <div class="audit-section">
                <h2>Electronic Signature Verification</h2>
                <table class="audit-table">
                    <thead>
                        <tr>
                            <th>Signer</th>
                            <th>Role</th>
                            <th>Signed At</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        {signers_html}
                    </tbody>
                </table>
            </div>

            <div class="footer">
                <p>Document ID: {context['edocument'].pk}</p>
                <p>Generated: {context['generated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p>This is an electronically signed document.</p>
            </div>
        </body>
        </html>
        """

    def _html_to_pdf(self, html: str) -> bytes:
        """Convert HTML to PDF using WeasyPrint."""
        try:
            from weasyprint import HTML
        except ImportError:
            logger.error("WeasyPrint is not installed. Install with: pip install weasyprint")
            raise ImportError(
                "WeasyPrint is required for PDF generation. "
                "Install with: pip install weasyprint"
            )

        # Generate PDF
        pdf_buffer = io.BytesIO()
        HTML(string=html).write_pdf(pdf_buffer)
        pdf_buffer.seek(0)

        return pdf_buffer.read()


def generate_edocument_pdf(edocument) -> bool:
    """
    Convenience function to generate PDF for an eDocument.

    Args:
        edocument: EDocument instance

    Returns:
        bool: True if successful
    """
    generator = EDocumentPDFGenerator(edocument)
    return generator.generate_and_save()
