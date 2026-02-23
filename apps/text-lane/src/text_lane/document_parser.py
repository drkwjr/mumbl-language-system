"""
Document parser for multiple file formats (EPUB, PDF, TXT, HTML).

Handles extraction of text from various formats while preserving
document structure for accurate source grounding.

Includes OCR support for scanned/image-based PDFs using Tesseract.
"""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ParsedDocument:
    """A parsed document with metadata"""

    text: str
    format: str  # 'epub', 'pdf', 'txt', 'html'
    metadata: Dict[str, Any]
    file_path: Optional[str] = None


class DocumentParser:
    """
    Parse documents from multiple formats.

    Supported formats:
    - EPUB (.epub)
    - PDF (.pdf)
    - Plain text (.txt, .md)
    - HTML (.html, .htm)
    """

    def __init__(self):
        self.supported_formats = {".epub", ".pdf", ".txt", ".md", ".html", ".htm"}

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse a document file.

        Args:
            file_path: Path to document file

        Returns:
            ParsedDocument with text and metadata

        Raises:
            ValueError: If format not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in self.supported_formats:
            raise ValueError(
                f"Unsupported format: {suffix}. " f"Supported: {', '.join(self.supported_formats)}"
            )

        # Route to appropriate parser
        if suffix == ".epub":
            return self._parse_epub(file_path)
        elif suffix == ".pdf":
            return self._parse_pdf(file_path)
        elif suffix in {".txt", ".md"}:
            return self._parse_text(file_path)
        elif suffix in {".html", ".htm"}:
            return self._parse_html(file_path)
        else:
            raise ValueError(f"Parser not implemented for: {suffix}")

    def _parse_epub(self, file_path: str) -> ParsedDocument:
        """Parse EPUB file"""
        try:
            import ebooklib
            from bs4 import BeautifulSoup
            from ebooklib import epub
        except ImportError:
            raise ImportError(
                "ebooklib and beautifulsoup4 required for EPUB parsing. "
                "Install with: pip install ebooklib beautifulsoup4"
            )

        book = epub.read_epub(file_path)

        # Extract metadata
        metadata = {
            "title": book.get_metadata("DC", "title"),
            "author": book.get_metadata("DC", "creator"),
            "language": book.get_metadata("DC", "language"),
            "publisher": book.get_metadata("DC", "publisher"),
        }

        # Extract text from all chapters
        chapters = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text = soup.get_text(separator="\n", strip=True)
                if text:
                    chapters.append(text)

        full_text = "\n\n".join(chapters)

        return ParsedDocument(text=full_text, format="epub", metadata=metadata, file_path=file_path)

    def _parse_pdf(self, file_path: str) -> ParsedDocument:
        """
        Parse PDF file with automatic OCR fallback.

        Strategy:
        1. Try normal text extraction first (fast)
        2. If < 100 chars extracted, assume scanned PDF
        3. Fall back to OCR (slower but works on scanned documents)
        """
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError(
                "PyPDF2 required for PDF parsing. " "Install with: pip install PyPDF2"
            )

        reader = PdfReader(file_path)

        # Extract metadata
        metadata = {
            "title": reader.metadata.title if reader.metadata else None,
            "author": reader.metadata.author if reader.metadata else None,
            "pages": len(reader.pages),
        }

        # Try normal text extraction first
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        full_text = "\n\n".join(pages)

        # If very little text extracted, likely scanned/image PDF
        if len(full_text.strip()) < 100:
            print(f"⚠️  Low text extraction ({len(full_text)} chars) - attempting OCR...")
            metadata["extraction_method"] = "ocr"
            full_text = self._ocr_pdf(file_path)
            metadata["ocr_applied"] = True
        else:
            metadata["extraction_method"] = "native"
            metadata["ocr_applied"] = False

        return ParsedDocument(text=full_text, format="pdf", metadata=metadata, file_path=file_path)

    def _parse_text(self, file_path: str) -> ParsedDocument:
        """Parse plain text file"""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        metadata = {
            "filename": Path(file_path).name,
            "size": os.path.getsize(file_path),
        }

        return ParsedDocument(text=text, format="txt", metadata=metadata, file_path=file_path)

    def _parse_html(self, file_path: str) -> ParsedDocument:
        """Parse HTML file"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError(
                "beautifulsoup4 required for HTML parsing. "
                "Install with: pip install beautifulsoup4"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract title from <title> tag
        title = soup.title.string if soup.title else None

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        metadata = {
            "title": title,
            "filename": Path(file_path).name,
        }

        return ParsedDocument(text=text, format="html", metadata=metadata, file_path=file_path)

    def _ocr_pdf(self, file_path: str, language: str = "eng") -> str:
        """
        OCR a scanned PDF using Tesseract.

        Args:
            file_path: Path to PDF file
            language: Tesseract language code (default: 'eng')
                     Note: Somali and Akan not in standard packs,
                     but English OCR works for Latin script

        Returns:
            Extracted text from all pages
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image and pytesseract required for OCR. "
                "Install with: pip install pdf2image pytesseract"
            )

        print(f"   Converting PDF to images...")

        # Convert PDF pages to images
        # Using lower DPI (200) for speed; increase to 300 for better quality
        try:
            images = convert_from_path(file_path, dpi=200, fmt="jpeg")
        except Exception as e:
            warnings.warn(f"PDF to image conversion failed: {e}")
            return ""

        print(f"   OCR processing {len(images)} pages...")

        # OCR each page
        page_texts = []
        for i, image in enumerate(images, 1):
            try:
                # Run Tesseract OCR
                text = pytesseract.image_to_string(
                    image, lang=language, config="--psm 1"  # Automatic page segmentation
                )
                page_texts.append(text)

                # Progress indicator
                if i % 10 == 0:
                    print(f"      Processed {i}/{len(images)} pages...")

            except Exception as e:
                warnings.warn(f"OCR failed on page {i}: {e}")
                continue

        full_text = "\n\n".join(page_texts)
        print(f"   ✓ OCR complete: {len(full_text):,} characters extracted")

        return full_text
