"""
Simple HTTP server for serving WebApp files.
This is for development purposes. In production, use nginx or similar.
"""

import os
from utils.logger import get_logger
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

logger = get_logger(__name__)


class WebAppHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving WebApp files with proper headers."""

    def __init__(self, *args, **kwargs):
        # Set directory to webapp folder
        webapp_dir = Path(__file__).parent
        super().__init__(*args, directory=str(webapp_dir), **kwargs)

    def end_headers(self):
        """Add CORS and cache headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS."""
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"WebApp Server: {format % args}")


class WebAppServer:
    """Simple HTTP server for WebApp development."""

    def __init__(self, port=8080):
        """
        Initialize WebApp server.

        Args:
            port: Port to serve on (default: 8080)
        """
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the HTTP server in a separate thread."""
        try:
            self.server = HTTPServer(('', self.port), WebAppHandler)
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.daemon = True
            self.thread.start()
            logger.info(f"WebApp server started on port {self.port}")
            logger.info(f"WebApp URL: http://localhost:{self.port}/setup_form.html")
            logger.info("For production, use ngrok or deploy to HTTPS server")
        except Exception as e:
            logger.error(f"Failed to start WebApp server: {e}")
            raise

    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            logger.info("WebApp server stopped")


def get_webapp_url(local_port=8080):
    """
    Get the WebApp URL based on environment.

    For development, this returns localhost URL.
    For production, this should return the deployed HTTPS URL.

    Args:
        local_port: Port for local development

    Returns:
        str: WebApp URL
    """
    # Check for production URL in environment
    webapp_url = os.getenv('WEBAPP_URL')

    if webapp_url:
        # Production URL from environment
        return webapp_url

    # Development URL
    # Note: Telegram WebApp requires HTTPS in production
    # For local testing, use ngrok or similar service
    return f"http://localhost:{local_port}/setup_form.html"


# Instructions for deployment
DEPLOYMENT_INSTRUCTIONS = """
WebApp Deployment Instructions:

1. For local development testing with Telegram:
   - Install ngrok: https://ngrok.com/
   - Run: ngrok http 8080
   - Copy the HTTPS URL and set WEBAPP_URL environment variable

2. For production deployment:
   Option A - Static hosting (recommended):
   - Deploy setup_form.html to GitHub Pages, Netlify, Vercel, etc.
   - Set WEBAPP_URL to the deployed URL

   Option B - Serve with bot:
   - Deploy bot with nginx/Apache to serve static files
   - Configure HTTPS with Let's Encrypt
   - Set WEBAPP_URL to https://your-domain.com/webapp/setup_form.html

3. Update the URL in src/handlers/setup.py:
   - Replace webapp_url variable with actual URL
   - Or use environment variable WEBAPP_URL

Important: Telegram WebApp requires HTTPS in production!
"""

if __name__ == "__main__":
    # Test server
    print("Starting WebApp development server...")
    print(DEPLOYMENT_INSTRUCTIONS)
    server = WebAppServer(8080)
    server.start()
    print(f"\nServer running at: http://localhost:8080/setup_form.html")
    print("Press Ctrl+C to stop")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped")