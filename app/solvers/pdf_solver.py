import logging
import json
import tempfile
import os
from typing import Dict, Any
import fitz
from openai import OpenAI as OpenAIClient

logger = logging.getLogger(__name__)
def get_client():
    return OpenAIClient()


async def solve_pdf_analysis(quiz_data: Dict[str, Any], analysis: Dict[str, Any], browser) -> Any:
    """Solve quiz that requires PDF data analysis"""
    logger.info("Quiz requires PDF analysis")
    
    quiz_text = quiz_data['question']
    
    import re
    pdf_urls = re.findall(r'https?://[^\s\]<>"\']+\.pdf', quiz_text, re.IGNORECASE)
    
    if not pdf_urls:
        logger.error("Could not find PDF URL")
        raise Exception("No PDF URL found in quiz")
    
    pdf_url = pdf_urls[0]
    logger.info(f"Found PDF URL: {pdf_url}")
    
    pdf_data = await browser.download_file(pdf_url)
    logger.info(f"Downloaded PDF: {len(pdf_data)} bytes")
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(pdf_data)
        tmp_path = tmp.name
    
    try:
        pdf_doc = fitz.open(tmp_path)
        logger.info(f"PDF has {pdf_doc.page_count} pages")
        
        full_text = ""
        for page_num in range(pdf_doc.page_count):
            page = pdf_doc[page_num]
            text = page.get_text()
            full_text += f"\n--- Page {page_num + 1} ---\n{text}"
        
        logger.info(f"Extracted text (first 300 chars): {full_text[:300]}")
        
        extract_prompt = f"""Extract the answer from this PDF.

Question: {quiz_text}

PDF Content:
{full_text}

Respond: {{"answer": <value>}}

JSON only."""

        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Extract precise answers from PDF content."},
                {"role": "user", "content": extract_prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        answer = result['answer']
        logger.info(f"PDF answer: {answer}")
        return answer
        
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        pdf_doc.close()
