"""
LLM Agent - Handles LLM interactions for solving quiz questions
"""
import os
import logging
import json
import base64
import re
from typing import Any, Optional, Dict, List
from openai import AsyncOpenAI
from playwright.async_api import Page
import aiohttp
import pandas as pd
from io import BytesIO
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

logger = logging.getLogger(__name__)

if not PDF_AVAILABLE:
    logger.warning("PyPDF2 not available, PDF processing will be limited")


class LLMAgent:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    async def solve(
        self,
        question: str,
        page: Page,
        url: str
    ) -> Any:
        """
        Solve a quiz question using LLM with access to various tools.
        """
        # Extract information from the question
        context = await self._gather_context(question, page, url)
        
        # Download and process any files mentioned
        files_data = await self._process_files_from_question(question, page, url)
        
        # Build prompt for LLM
        system_prompt = """You are an expert data analyst and problem solver. You can:
1. Scrape and extract data from web pages
2. Download and process files (PDFs, CSVs, JSON, etc.)
3. Clean and transform data
4. Perform statistical analysis and aggregations
5. Generate visualizations
6. Answer questions based on data analysis

When solving a quiz question:
- Read the question carefully
- Identify what data you need
- Extract or download the required data
- Process and analyze it
- Provide the exact answer requested (number, string, boolean, etc.)

Be precise and accurate. Show your reasoning but provide the final answer in the requested format.
Your final answer should be just the value requested, not an explanation."""
        
        user_prompt = f"""Question: {question}

Context from page:
{context}

{files_data if files_data else ''}

Solve this question step by step. Provide your final answer in the exact format requested.
If the answer is a number, provide just the number.
If the answer is text, provide just the text.
If the answer is a boolean, provide true or false.
If the answer requires a file, provide it as base64."""
        
        # Call LLM with function calling for data processing
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=4000
        )
        
        answer_text = response.choices[0].message.content
        
        # Try to extract the answer from the response
        answer = self._extract_answer(answer_text, question)
        
        # If LLM suggests downloading files, do it
        if isinstance(answer, str) and ("download" in answer.lower() or "file" in answer.lower()):
            # Try to download and process files
            processed_data = await self._process_files_from_question(question, page, url, full_process=True)
            if processed_data:
                # Re-query with processed data
                user_prompt_with_data = f"{user_prompt}\n\nProcessed data:\n{processed_data}"
                response2 = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt_with_data}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
                answer_text = response2.choices[0].message.content
                answer = self._extract_answer(answer_text, question)
        
        return answer
    
    async def _gather_context(
        self,
        question: str,
        page: Page,
        url: str
    ) -> str:
        """
        Gather relevant context from the page and question.
        """
        context_parts = []
        
        # Get page text
        try:
            page_text = await page.evaluate("() => document.body.innerText")
            context_parts.append(f"Page content:\n{page_text[:3000]}")
        except Exception as e:
            logger.debug(f"Error getting page text: {e}")
        
        # Look for download links
        try:
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(a => ({text: a.textContent.trim(), href: a.href}));
                }
            """)
            
            download_links = [
                link for link in links
                if any(ext in link['href'].lower() for ext in ['.pdf', '.csv', '.json', '.xlsx', '.txt', '.xls'])
            ]
            
            if download_links:
                context_parts.append(f"Download links found: {json.dumps(download_links, indent=2)}")
        except Exception as e:
            logger.debug(f"Error getting links: {e}")
        
        # Check for data in the page
        try:
            # Look for tables
            tables = await page.evaluate("""
                () => {
                    const tables = Array.from(document.querySelectorAll('table'));
                    return tables.map((t, i) => ({
                        index: i,
                        text: t.innerText,
                        html: t.outerHTML.substring(0, 5000)
                    }));
                }
            """)
            if tables:
                for table in tables:
                    context_parts.append(f"Table {table['index']}:\n{table['text']}")
        except Exception as e:
            logger.debug(f"Error getting tables: {e}")
        
        # Look for JSON data
        try:
            json_scripts = await page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts.map(s => s.textContent).filter(t => t && t.includes('{'));
                }
            """)
            if json_scripts:
                context_parts.append(f"Found {len(json_scripts)} script tags with potential JSON")
        except:
            pass
        
        return "\n\n".join(context_parts) if context_parts else "No context found"
    
    def _extract_answer(self, llm_response: str, question: str) -> Any:
        """
        Extract the answer from LLM response.
        """
        # Try to find JSON in response (handle multi-line)
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if "answer" in data:
                    return data["answer"]
            except:
                pass
        
        # Try to find answer: pattern
        answer_pattern = re.search(r'answer[:\s]+([^\n]+)', llm_response, re.IGNORECASE)
        if answer_pattern:
            answer_str = answer_pattern.group(1).strip()
            # Try to parse as number
            try:
                if '.' in answer_str:
                    return float(answer_str)
                return int(answer_str)
            except:
                # Check boolean
                if answer_str.lower() in ['true', 'false']:
                    return answer_str.lower() == 'true'
                return answer_str
        
        # Try to find number (more comprehensive)
        # Look for numbers that might be answers (not just any number)
        number_patterns = [
            r'\b(\d+\.?\d*)\b',  # Simple number
            r'[=:]\s*(\d+\.?\d*)',  # Number after = or :
            r'is\s+(\d+\.?\d*)',  # "is 123"
            r'are\s+(\d+\.?\d*)',  # "are 123"
        ]
        
        for pattern in number_patterns:
            number_match = re.search(pattern, llm_response, re.IGNORECASE)
            if number_match:
                num_str = number_match.group(1)
                try:
                    if '.' in num_str:
                        return float(num_str)
                    return int(num_str)
                except:
                    continue
        
        # Try to find boolean
        if re.search(r'\btrue\b', llm_response, re.IGNORECASE):
            return True
        if re.search(r'\bfalse\b', llm_response, re.IGNORECASE):
            return False
        
        # Try to extract base64 data URI
        base64_match = re.search(r'data:[^;]+;base64,([A-Za-z0-9+/=]+)', llm_response)
        if base64_match:
            return base64_match.group(0)  # Return full data URI
        
        # Return as string (last resort)
        # Try to get the last line or a concise answer
        lines = llm_response.strip().split('\n')
        if len(lines) > 1:
            # Check last line for answer
            last_line = lines[-1].strip()
            if len(last_line) < 100:  # Likely an answer, not explanation
                return last_line
        
        return llm_response.strip()
    
    async def _process_files_from_question(
        self,
        question: str,
        page: Page,
        url: str,
        full_process: bool = False
    ) -> Optional[str]:
        """
        Process files mentioned in the question.
        """
        try:
            # Find download links
            links = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(a => ({text: a.textContent.trim(), href: a.href}));
                }
            """)
            
            file_links = [
                link for link in links
                if any(ext in link['href'].lower() for ext in ['.pdf', '.csv', '.json', '.xlsx', '.txt', '.xls'])
            ]
            
            if not file_links:
                return None
            
            processed_data = []
            
            for link in file_links:
                file_url = link['href']
                file_type = self._get_file_type(file_url)
                
                logger.info(f"Processing file: {file_url} (type: {file_type})")
                
                try:
                    data = await self.download_and_process_file(file_url, file_type)
                    
                    if file_type == "csv":
                        # Convert to readable format
                        if isinstance(data, list) and len(data) > 0:
                            df = pd.DataFrame(data)
                            processed_data.append(f"CSV file ({file_url}):\n{df.to_string()}\n\nSummary:\n{df.describe().to_string()}")
                        else:
                            processed_data.append(f"CSV file ({file_url}): {json.dumps(data, indent=2)}")
                    elif file_type == "json":
                        processed_data.append(f"JSON file ({file_url}):\n{json.dumps(data, indent=2)}")
                    elif file_type == "pdf":
                        # Extract text from PDF
                        text = self._extract_pdf_text(data)
                        processed_data.append(f"PDF file ({file_url}) text:\n{text[:5000]}")
                    else:
                        processed_data.append(f"File ({file_url}): {str(data)[:1000]}")
                
                except Exception as e:
                    logger.error(f"Error processing file {file_url}: {e}")
                    processed_data.append(f"Error processing {file_url}: {str(e)}")
            
            return "\n\n".join(processed_data) if processed_data else None
        
        except Exception as e:
            logger.error(f"Error in _process_files_from_question: {e}")
            return None
    
    def _get_file_type(self, url: str) -> str:
        """Determine file type from URL."""
        url_lower = url.lower()
        if '.pdf' in url_lower:
            return "pdf"
        elif '.csv' in url_lower:
            return "csv"
        elif '.json' in url_lower:
            return "json"
        elif '.xlsx' in url_lower or '.xls' in url_lower:
            return "excel"
        elif '.txt' in url_lower:
            return "txt"
        else:
            return "unknown"
    
    def _extract_pdf_text(self, base64_data: str) -> str:
        """Extract text from base64-encoded PDF."""
        if not PDF_AVAILABLE:
            return "PDF processing not available (PyPDF2 not installed)"
        try:
            pdf_bytes = base64.b64decode(base64_data)
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return f"Error extracting PDF: {str(e)}"
    
    async def download_and_process_file(
        self,
        url: str,
        file_type: str
    ) -> Any:
        """
        Download a file and process it based on type.
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.read()
                
                if file_type == "pdf":
                    # Return base64 for PDF
                    return base64.b64encode(content).decode('utf-8')
                
                elif file_type == "csv":
                    # Parse CSV
                    try:
                        df = pd.read_csv(io.BytesIO(content))
                        return df.to_dict('records')
                    except:
                        # Try with different encodings
                        for encoding in ['utf-8', 'latin-1', 'iso-8859-1']:
                            try:
                                df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                                return df.to_dict('records')
                            except:
                                continue
                        raise
                
                elif file_type == "json":
                    return json.loads(content.decode('utf-8'))
                
                elif file_type == "excel":
                    df = pd.read_excel(io.BytesIO(content))
                    return df.to_dict('records')
                
                elif file_type == "txt":
                    return content.decode('utf-8', errors='ignore')
                
                else:
                    return content

