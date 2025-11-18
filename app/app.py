"""
Main application entry point
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Starting AI Questionnaire Generator Application")
    
    try:
        import streamlit.web.cli as stcli
        import sys
        
        sys.argv = [
            "streamlit",
            "run",
            str(app_dir / "streamlit.py"),
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--theme.base=light"
        ]
        
        stcli.main()
        

    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        raise

if __name__ == "__main__":
    main()
