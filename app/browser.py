from playwright.async_api import async_playwright, Browser, Page
import logging
import re
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class QuizBrowser:
    """Handles all browser automation for quiz solving"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
    
    async def start(self):
        """Initialize the browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,  # Run without GUI
            args=['--no-sandbox', '--disable-setuid-sandbox']  # Required for some Linux environments
        )
        logger.info("Browser started successfully")
    
    async def stop(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser stopped")
    
    async def fetch_quiz_page(self, url: str) -> Dict[str, str]:
        """
        Fetch and render a quiz page, extract the content
        
        Args:
            url: The quiz URL to visit
            
        Returns:
            Dict with 'question', 'submit_url', and 'raw_html'
        """
        if not self.browser:
            await self.start()
        
        logger.info(f"Fetching quiz page: {url}")
        
        # Create a new page
        page: Page = await self.browser.new_page()
        
        try:
            # Navigate to the URL and wait for content to load
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait a bit for JavaScript to execute
            await page.wait_for_timeout(2000)
            
            # Get the rendered content
            content = await page.content()
            
            # Try to extract text from #result first, fallback to body
            try:
                result_text = await page.locator("#result").inner_text(timeout=5000)
                logger.info("Extracted content from #result element")
            except:
                # Fallback: get all text from body
                result_text = await page.locator("body").inner_text()
                logger.info("Extracted content from body element")
            
            logger.info(f"Extracted quiz content (first 200 chars): {result_text[:200]}...")
            
            # Extract submit URL using regex
            submit_url = self._extract_submit_url(result_text)
            
            return {
                "question": result_text,
                "submit_url": submit_url,
                "raw_html": content,
                "quiz_url": url
            }
            
        except Exception as e:
            logger.error(f"Error fetching quiz page: {e}")
            raise
        finally:
            await page.close()

    
    def _extract_submit_url(self, text: str) -> Optional[str]:
        """
        Extract the submit URL from quiz text
        
        Looks for patterns like:
        - "Post your answer to https://example.com/submit"
        - "Submit to: https://example.com/submit"
        """
        # Pattern to find URLs in the text
        url_pattern = r'https?://[^\s<>"]+/submit[^\s<>"]*'
        match = re.search(url_pattern, text)
        
        if match:
            url = match.group(0)
            # Clean up any trailing punctuation
            url = url.rstrip('.,;:')
            logger.info(f"Extracted submit URL: {url}")
            return url
        
        logger.warning("Could not extract submit URL from quiz text")
        return None
    
    async def download_file(self, url: str) -> bytes:
        """
        Download a file from a URL
        
        Args:
            url: The file URL to download
            
        Returns:
            File content as bytes
        """
        if not self.browser:
            await self.start()
        
        logger.info(f"Downloading file: {url}")
        
        page = await self.browser.new_page()
        
        try:
            # Use page.request to download files
            response = await page.request.get(url)
            
            if response.ok:
                file_content = await response.body()
                logger.info(f"Downloaded {len(file_content)} bytes")
                return file_content
            else:
                raise Exception(f"Failed to download file: HTTP {response.status}")
                
        finally:
            await page.close()


# Global browser instance
quiz_browser = QuizBrowser()
