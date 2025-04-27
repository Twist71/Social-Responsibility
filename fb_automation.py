#!/usr/bin/env python3
import os
import asyncio
import logging
from datetime import datetime
import dotenv
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[]) # Empty root handler
logger = logging.getLogger(__name__)

# File handler for detailed logs (DEBUG and above)
file_handler = logging.FileHandler("fb_automation.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

# Console handler for summary logs (INFO and above)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console)

# Set the overall logger level to DEBUG to capture everything
logger.setLevel(logging.DEBUG)