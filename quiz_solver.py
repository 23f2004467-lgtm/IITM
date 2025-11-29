"""
Quiz Solver - Handles quiz page scraping, parsing, and solving
"""
import asyncio
import json
import logging
import base64
import re
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
from llm_agent import LLMAgent

logger = logging.getLogger(__name__)


class QuizSolver:
    def __init__(self, email: str, secret: str, timeout_seconds: int = 180):
        self.email = email
        self.secret = secret
        self.timeout_seconds = timeout_seconds
        self.llm_agent = LLMAgent()
    
    async def solve_quiz(self, initial_url: str) -> Dict[str, Any]:
        """
        Main method to solve a quiz starting from the initial URL.
        Handles the entire quiz flow including multiple questions.
        """
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                current_url = initial_url
                start_time = asyncio.get_event_loop().time()
                max_retries = 2
                
                while current_url:
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > self.timeout_seconds:
                        logger.error("Timeout exceeded")
                        return {
                            "error": "Timeout exceeded",
                            "reason": "Quiz solving took longer than 3 minutes"
                        }
                    
                    logger.info(f"Solving quiz at: {current_url}")
                    
                    # Get quiz question
                    quiz_data = await self._get_quiz_question(page, current_url)
                    if not quiz_data:
                        return {
                            "error": "Failed to parse quiz",
                            "reason": "Could not extract quiz question from page"
                        }
                    
                    # Submit answer
                    submit_url = quiz_data.get("submit_url")
                    if not submit_url:
                        return {
                            "error": "No submit URL found",
                            "reason": "Quiz page did not contain submit URL"
                        }
                    
                    # Try solving with retries
                    answer = None
                    result = None
                    retry_count = 0
                    
                    while retry_count <= max_retries:
                        # Solve the question
                        answer = await self._solve_question(quiz_data, page)
                        
                        # Submit answer
                        result = await self._submit_answer(
                            submit_url,
                            current_url,
                            answer
                        )
                        
                        if result.get("correct"):
                            logger.info("Answer correct!")
                            break
                        else:
                            logger.warning(f"Answer incorrect (attempt {retry_count + 1}): {result.get('reason')}")
                            retry_count += 1
                            
                            # If we have a next URL, we can skip retrying
                            if result.get("url"):
                                logger.info("Moving to next URL instead of retrying")
                                break
                    
                    # Handle result
                    if result.get("correct"):
                        current_url = result.get("url")  # Next URL or None if done
                    else:
                        # Check if we can move to next URL
                        if result.get("url"):
                            current_url = result.get("url")
                        else:
                            # No more URLs, quiz might be over or we failed
                            logger.warning("No more URLs and answer was incorrect")
                            current_url = None
                
                return {
                    "status": "completed",
                    "message": "Quiz solving completed"
                }
        
        except Exception as e:
            logger.error(f"Error in solve_quiz: {e}", exc_info=True)
            raise
        finally:
            if browser:
                await browser.close()
    
    async def _get_quiz_question(self, page: Page, url: str) -> Optional[Dict[str, Any]]:
        """
        Navigate to quiz URL and extract the question and submit URL.
        """
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for JavaScript to render
            await page.wait_for_timeout(2000)
            
            # Extract content from #result div (common pattern)
            result_content = await page.evaluate("""
                () => {
                    const result = document.querySelector('#result');
                    return result ? result.innerHTML : '';
                }
            """)
            
            if not result_content:
                # Try to get all text content
                result_content = await page.evaluate("() => document.body.innerText")
            
            # Decode base64 if present (handle multiple patterns)
            if "atob" in result_content or "base64" in result_content.lower():
                # Try different base64 patterns
                patterns = [
                    r'atob\(`([^`]+)`\)',
                    r'atob\(["\']([^"\']+)["\']\)',
                    r'base64[:\s]+([A-Za-z0-9+/=]+)',
                ]
                for pattern in patterns:
                    base64_match = re.search(pattern, result_content)
                    if base64_match:
                        try:
                            decoded = base64.b64decode(base64_match.group(1)).decode('utf-8')
                            result_content = decoded
                            break
                        except Exception as e:
                            logger.debug(f"Failed to decode base64: {e}")
                            continue
            
            # Parse the question and extract submit URL (try multiple patterns)
            submit_url = None
            patterns = [
                r'https?://[^\s<>"\'\)]+/submit[^\s<>"\'\)]*',
                r'Post.*?to\s+(https?://[^\s<>"\'\)]+)',
                r'submit.*?to\s+(https?://[^\s<>"\'\)]+)',
                r'https?://[^\s<>"\'\)]+/submit',
            ]
            for pattern in patterns:
                submit_url_match = re.search(pattern, result_content, re.IGNORECASE)
                if submit_url_match:
                    submit_url = submit_url_match.group(0) if submit_url_match.lastindex == 0 else submit_url_match.group(1)
                    break
            
            # If no submit URL found, use default submit endpoint
            if not submit_url:
                # Extract origin from current URL
                origin_match = re.search(r'(https?://[^/]+)', url)
                if origin_match:
                    submit_url = origin_match.group(1) + "/submit"
                else:
                    # Default fallback
                    submit_url = "https://tds-llm-analysis.s-anand.net/submit"
            
            # Extract question text
            question_text = result_content
            
            return {
                "question": question_text,
                "submit_url": submit_url,
                "page": page,
                "url": url
            }
        
        except Exception as e:
            logger.error(f"Error getting quiz question: {e}")
            return None
    
    async def _solve_question(
        self,
        quiz_data: Dict[str, Any],
        page: Page
    ) -> Any:
        """
        Use LLM agent to solve the question.
        """
        question = quiz_data.get("question", "")
        url = quiz_data.get("url", "")
        
        logger.info(f"Solving question: {question[:100]}...")
        
        # Use LLM agent to solve
        answer = await self.llm_agent.solve(
            question=question,
            page=page,
            url=url
        )
        
        return answer
    
    async def _submit_answer(
        self,
        submit_url: str,
        quiz_url: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit answer to the submit endpoint.
        """
        import aiohttp
        
        payload = {
            "email": self.email,
            "secret": self.secret,
            "url": quiz_url,
            "answer": answer
        }
        
        logger.info(f"Submitting answer to: {submit_url}")
        logger.debug(f"Payload: {json.dumps(payload, default=str)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    submit_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    # Handle non-JSON responses
                    try:
                        result = await response.json()
                    except Exception:
                        # If response is not JSON, return error
                        text = await response.text()
                        logger.error(f"Non-JSON response from submit endpoint: {text}")
                        return {
                            "correct": False,
                            "reason": f"Invalid response from submit endpoint: {text[:200]}"
                        }
                    return result
        except aiohttp.ClientError as e:
            logger.error(f"Network error submitting answer: {e}")
            return {
                "correct": False,
                "reason": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return {
                "correct": False,
                "reason": f"Failed to submit: {str(e)}"
            }

