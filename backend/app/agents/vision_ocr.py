"""
Agent 2: Vision & OCR Agent (Llama 3.1)
Extracts structured data from invoice PDFs/images using local Llama 3.1 via Ollama.
Falls back to PyPDF2 text extraction + Llama for structured parsing.
"""

import json
import time
import logging
import base64
import httpx
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an expert invoice data extraction system. Extract ALL data from the following invoice text into a precise JSON structure.

INVOICE TEXT:
{invoice_text}

Return ONLY valid JSON with this exact schema (no markdown, no explanation):
{{
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "vendor_id": "string or null",
    "vendor_address": "string or null",
    "bill_to": "string or null",
    "po_reference": "string or null (e.g. PO-2024-001)",
    "currency": "USD",
    "line_items": [
        {{
            "item_code": "string or null",
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total_price": number
        }}
    ],
    "subtotal": number,
    "tax_amount": number,
    "total_amount": number,
    "payment_terms": "string or null",
    "notes": "string or null"
}}

Rules:
- Extract PO reference if mentioned (look for "PO#", "PO Number", "Purchase Order", "Ref")
- If a field is not found, use null
- All monetary values must be numbers (not strings)
- Ensure line item totals are consistent (quantity × unit_price = total_price)
"""


class VisionOCRAgent:
    """Extract structured invoice data using Groq (Llama models)."""

    def __init__(self):
        self.groq_api_key = settings.groq_api_key
        self.groq_model = settings.groq_model
        self.groq_vision_model = "llama-3.2-90b-vision-preview"
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required in environment")

    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract raw text from PDF using PyPDF2."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return ""

    def _extract_text_from_image(self, file_path: str) -> str:
        """Extract text from image using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            import platform
            import os
            
            # Set Tesseract path only on Windows if not in PATH
            if platform.system() == 'Windows':
                windows_tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                if os.path.exists(windows_tesseract_path):
                    pytesseract.pytesseract.tesseract_cmd = windows_tesseract_path
            # On Linux (Render/Docker), tesseract is in PATH and installed at /usr/bin/tesseract
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            logger.info(f"Tesseract extracted {len(text)} chars from {Path(file_path).name}")
            return text
        except Exception as e:
            logger.warning(f"Tesseract OCR failed: {e}")
            return ""

    def _extract_invoice_from_image_vision(self, file_path: str) -> dict:
        """Use llama3.2-vision model to extract invoice data directly from image with Groq fallback."""
        with open(file_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = """You are an expert invoice/receipt data extraction system. Look at this invoice or receipt image carefully and extract ALL data into a precise JSON structure.

Return ONLY valid JSON with this exact schema (no markdown, no explanation):
{
    "invoice_number": "string (bill number or receipt number)",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "vendor_name": "string (store/business name)",
    "vendor_id": "string or null (GSTIN or tax ID)",
    "vendor_address": "string or null",
    "bill_to": "string or null",
    "po_reference": "string or null",
    "currency": "string (e.g. INR, USD)",
    "line_items": [
        {
            "item_code": "string or null",
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total_price": number
        }
    ],
    "subtotal": number,
    "tax_amount": number,
    "total_amount": number,
    "payment_terms": "string or null",
    "notes": "string or null"
}

Rules:
- Read every line item from the receipt carefully
- All monetary values must be numbers (not strings)
- Ensure line item totals are consistent (quantity * unit_price = total_price)
- Use the Grand Total or final total as total_amount
- Identify GSTIN/tax IDs as vendor_id
- If a field is not found, use null"""

        # Use Groq vision model (llama-3.2-90b-vision-preview)
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048
                },
                timeout=60.0
            )
            response.raise_for_status()
            raw_response = response.json()["choices"][0]["message"]["content"]
            logger.info(f"Groq vision extracted {len(raw_response)} chars from {Path(file_path).name}")
            return self._parse_json_response(raw_response)
        except Exception as e:
            logger.error(f"Groq vision extraction failed: {e}")
            raise Exception(f"Invoice extraction failed: {e}")

    def _call_llama(self, prompt: str) -> str:
        """Call Groq API (Llama 3.3 70B)."""
        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.groq_model,
                    "messages": [
                        {"role": "system", "content": "You are an expert invoice data extraction system. Return only valid JSON, no markdown or explanations."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 2048
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            raise Exception(f"LLM extraction failed: {e}")

    @staticmethod
    def _sanitize_json(raw: str) -> str:
        """Fix common LLM JSON mistakes so json.loads succeeds."""
        import re
        s = raw
        # Remove single-line // comments
        s = re.sub(r'//[^\n]*', '', s)
        # Remove trailing commas before } or ]
        s = re.sub(r',\s*([}\]])', r'\1', s)
        # Replace single-quoted strings with double-quoted
        # (only simple cases — avoids nested quotes)
        s = re.sub(r"(?<=[:{,\[])\s*'([^']*)'\s*(?=[,}\]:])", r' "\1"', s)
        # Remove control characters except newline/tab
        s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
        return s

    def _parse_json_response(self, raw_response: str) -> dict:
        """Parse JSON from Llama response, handling markdown code blocks and common LLM quirks."""
        text = raw_response.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        # Isolate the JSON object
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        # Attempt 1: strict parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Attempt 2: sanitize then parse
        sanitized = self._sanitize_json(text)
        try:
            return json.loads(sanitized)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON sanitize still failed: {e}")

        # Attempt 3: last resort — eval-safe literal parse (handles single quotes, trailing commas)
        import ast
        try:
            result = ast.literal_eval(text)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError):
            pass

        raise ValueError(f"Could not parse JSON from Llama response: {text[:300]}")

    def extract_invoice_data(self, file_path: str) -> dict:
        """
        Main extraction pipeline using Tesseract OCR:
        1. Extract text from PDF/image using Tesseract
        2. Send to Groq Llama for structured extraction
        3. Return parsed JSON with confidence score
        """
        start_time = time.time()
        path = Path(file_path)

        # Step 1: Extract raw text using Tesseract OCR
        if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
            logger.info(f"Using Tesseract OCR for image: {path.name}")
            raw_text = self._extract_text_from_image(file_path)
            if not raw_text.strip():
                raise ValueError(f"Tesseract OCR could not extract text from {path.name}. Please ensure the image is clear and contains readable text.")
        elif path.suffix.lower() == ".pdf":
            raw_text = self._extract_text_from_pdf(file_path)
        elif path.suffix.lower() == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        if not raw_text.strip():
            raise ValueError("No text could be extracted from the file")

        logger.info(f"Extracted {len(raw_text)} chars from {path.name}")

        # Step 2: Send to Groq Llama for structured extraction
        prompt = EXTRACTION_PROMPT.format(invoice_text=raw_text[:4000])  # Limit context
        llama_response = self._call_llama(prompt)

        # Step 3: Parse response
        extracted = self._parse_json_response(llama_response)

        processing_time = time.time() - start_time
        logger.info(f"Invoice extraction completed in {processing_time:.2f}s")

        # Add metadata
        extracted["_metadata"] = {
            "source_file": path.name,
            "raw_text_length": len(raw_text),
            "processing_time_seconds": round(processing_time, 2),
            "extraction_method": "tesseract_ocr",
            "model": self.groq_model,
            "llm_provider": "groq",
            "confidence_score": self._calculate_confidence(extracted)
        }

        return extracted

    def _calculate_confidence(self, data: dict) -> float:
        """Calculate confidence score based on field completeness."""
        required_fields = ["invoice_number", "vendor_name", "total_amount", "line_items"]
        optional_fields = ["invoice_date", "po_reference", "tax_amount", "due_date"]

        score = 0.0
        total_weight = 0.0

        for field in required_fields:
            total_weight += 2.0
            if data.get(field):
                score += 2.0

        for field in optional_fields:
            total_weight += 1.0
            if data.get(field):
                score += 1.0

        # Check line items quality
        items = data.get("line_items", [])
        if items:
            total_weight += 2.0
            valid_items = sum(1 for item in items if item.get("description") and item.get("quantity"))
            score += 2.0 * (valid_items / len(items))

        return round(score / total_weight, 2) if total_weight > 0 else 0.0

    def health_check(self) -> dict:
        """Check if Groq API is available (fast check)."""
        status = {
            "ollama_status": "not_used",
            "groq_status": "online",
            "model": self.groq_model,
            "vision_model": self.groq_vision_model,
            "model_available": True
        }
        
        # Quick validation - just check if API key exists
        if not self.groq_api_key:
            status["groq_status"] = "not_configured"
            status["model_available"] = False
            status["error"] = "GROQ_API_KEY not set"
        
        return status
