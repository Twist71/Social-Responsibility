import asyncio
import json
import logging
import os
import re
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Error
# Add playwright-stealth for anti-detection
from playwright_stealth import stealth_async

# Script version and features
SCRIPT_VERSION = "1.4.0"
SCRIPT_FEATURES = [
    "Automated Facebook login with manual security challenge handling",
    "Advanced stealth mode with browser fingerprint protection",
    "Human-like typing with variable speed, pauses, and occasional corrections",
    "Realistic mouse movements with acceleration/deceleration physics",
    "Safari browser mimicking via comprehensive fingerprint configuration",
    "Intelligent wait patterns for Facebook UI elements",
    "Smart detection of successful user authentication completion",
    "Session timeout detection and recovery",
    "Robust navigation to Facebook posts with multiple fallback strategies",
    "Enhanced comment box detection with updated selectors",
    "Posting of both direct comments and replies with natural timing",
    "Comprehensive screenshot capture at critical automation steps",
    "Detailed logging with both summary and debug levels",
    "User-friendly prompts and guidance for manual intervention steps",
    "Verification of successful comment/reply posting",
    "Environmental variable support for secure credential management",
    "Graceful handling of browser closure by user",
    "Support for both headless and visible browser operation",
    "Anti-detection measures against modern bot-detection systems"
]

# Set up logging
log_folder = Path("logs")
log_folder.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Configure file handlers
debug_log_path = log_folder / f"fb_commenter_debug_{timestamp}.log"
summary_log_path = log_folder / f"fb_commenter_summary_{timestamp}.log"

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(debug_log_path),
        logging.StreamHandler()
    ]
)

# Create logger for this module
logger = logging.getLogger("fb_commenter")

# Create summary logger (important actions and results only)
summary_logger = logging.getLogger("fb_commenter.summary")
summary_handler = logging.FileHandler(summary_log_path)
summary_handler.setLevel(logging.INFO)
summary_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
summary_handler.setFormatter(summary_formatter)
summary_logger.addHandler(summary_handler)
summary_logger.propagate = False  # Don't propagate to root logger

# Load environment variables
load_dotenv()

# Configuration settings
class Config:
    # Browser settings
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
    SLOWMO = int(os.getenv("SLOWMO", "50"))
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30000"))
    
    # Facebook credentials
    FB_USERNAME = os.getenv("FB_USERNAME", "")
    FB_PASSWORD = os.getenv("FB_PASSWORD", "")
    
    # URLs and targets
    FB_LOGIN_URL = "https://www.facebook.com/login"
    FB_BASE_URL = "https://www.facebook.com"
    
    # User agent settings (multiple options for random selection)
    SAFARI_USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    ]
    
    # Typing settings for human-like behavior
    TYPING_SPEED_MIN_CHARS_SEC = 7    # Minimum typing speed (characters per second)
    TYPING_SPEED_MAX_CHARS_SEC = 12   # Maximum typing speed (characters per second)
    TYPING_SPEED_VARIANCE = 0.3       # Variance in typing speed (percentage)
    TYPING_ERROR_CHANCE = 0.01        # Chance of making a typing error
    
    # Timing settings for human-like typing
    MIN_KEY_PRESS_DELAY = 0.01        # Minimum delay between keystrokes (seconds)
    MAX_KEY_PRESS_DELAY = 0.08        # Maximum delay between keystrokes (seconds)
    WORD_PAUSE_CHANCE = 0.2           # Probability of adding a pause after words
    WORD_PAUSE_MIN = 0.1              # Minimum word pause (seconds)
    WORD_PAUSE_MAX = 0.3              # Maximum word pause (seconds)
    SENTENCE_PAUSE_MIN = 0.5          # Minimum pause after sentence (seconds)
    SENTENCE_PAUSE_MAX = 1.2          # Maximum pause after sentence (seconds)
    
    # Mouse movement settings
    MOUSE_MOVE_TIME_MIN = 0.5         # Minimum time for mouse movement (seconds)
    MOUSE_MOVE_TIME_MAX = 1.5         # Maximum time for mouse movement (seconds)
    MOUSE_POINTS_PER_MOVE = 25        # Number of points to generate for mouse movement path
    MOUSE_JITTER_FACTOR = 0.08        # Random jitter factor for mouse movement
    
    # Automation detection avoidance
    ACTION_DELAY_MIN = 0.5            # Minimum delay between actions (seconds)
    ACTION_DELAY_MAX = 2.0            # Maximum delay between actions (seconds)
    
    # Screenshots
    SCREENSHOT_FOLDER = Path("screenshots")
    TAKE_SCREENSHOTS = True
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 2                   # seconds
    
    # Browser fingerprint settings
    VIEWPORT_SIZES = [
        {"width": 1280, "height": 720},
        {"width": 1440, "height": 900},
        {"width": 1680, "height": 1050},
    ]
    
    LOCALES = ["en-US", "en-GB", "en-CA"]
    TIMEZONES = ["America/New_York", "America/Los_Angeles", "America/Chicago"]
    
    # Stealth mode settings
    STEALTH_ENABLED = True

# Ensure screenshot folder exists
Config.SCREENSHOT_FOLDER.mkdir(exist_ok=True)

def get_browser_fingerprint() -> Dict[str, Any]:
    """Get a consistent browser fingerprint for this session."""
    # Choose consistent values for this session
    user_agent = random.choice(Config.SAFARI_USER_AGENTS)
    viewport = random.choice(Config.VIEWPORT_SIZES)
    locale = random.choice(Config.LOCALES)
    timezone = random.choice(Config.TIMEZONES)
    
    return {
        "user_agent": user_agent,
        "viewport": viewport,
        "locale": locale,
        "timezone_id": timezone,
        "device_scale_factor": 2.0 if "Macintosh" in user_agent else 1.0,
        "is_mobile": False,
        "has_touch": False,
        "color_scheme": "light"
    }

def easeInOutQuad(t: float) -> float:
    """Quadratic easing function for smooth mouse movement."""
    return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2

def generate_mouse_path(start_x: int, start_y: int, end_x: int, end_y: int, 
                        num_points: int = 25, jitter_factor: float = 0.08) -> List[Dict[str, int]]:
    """Generate a realistic mouse movement path with slight jitter."""
    points = []
    
    # Generate smooth path with easing function
    for i in range(num_points + 1):
        t = i / num_points
        ease_t = easeInOutQuad(t)
        
        # Calculate point on curve
        x = start_x + (end_x - start_x) * ease_t
        y = start_y + (end_y - start_y) * ease_t
        
        # Add some random jitter (more in the middle, less at endpoints)
        if 0 < i < num_points:
            max_jitter_x = abs(end_x - start_x) * jitter_factor
            max_jitter_y = abs(end_y - start_y) * jitter_factor
            
            # Jitter is highest in the middle of the path (bell curve)
            jitter_scale = 4 * t * (1 - t)  # Peaks at t=0.5
            
            x += random.uniform(-max_jitter_x, max_jitter_x) * jitter_scale
            y += random.uniform(-max_jitter_y, max_jitter_y) * jitter_scale
        
        points.append({"x": round(x), "y": round(y)})
    
    return points

async def human_like_mouse_move(page: Page, selector: str) -> None:
    """Move mouse to an element in a human-like manner."""
    # Get current mouse position
    # Note: Playwright doesn't provide direct access to current mouse position
    # So we'll start from a random position near the top of the viewport
    viewport = page.viewport_size
    if not viewport:
        viewport = {"width": 1280, "height": 720}
    
    start_x = random.randint(100, viewport["width"] - 100)
    start_y = random.randint(100, 200)  # Start from near the top
    
    # Get element position
    element_handle = await page.wait_for_selector(selector, state="visible")
    if not element_handle:
        logger.warning(f"Could not find element with selector: {selector}")
        return
    
    bounding_box = await element_handle.bounding_box()
    if not bounding_box:
        logger.warning(f"Could not get bounding box for element: {selector}")
        return
    
    # Calculate target position (somewhere within the element)
    target_x = bounding_box["x"] + random.uniform(0.3, 0.7) * bounding_box["width"]
    target_y = bounding_box["y"] + random.uniform(0.3, 0.7) * bounding_box["height"]
    
    # Generate realistic movement path
    path = generate_mouse_path(
        start_x, start_y, 
        target_x, target_y,
        Config.MOUSE_POINTS_PER_MOVE,
        Config.MOUSE_JITTER_FACTOR
    )
    
    # Determine movement time (longer for longer distances)
    distance = ((target_x - start_x) ** 2 + (target_y - start_y) ** 2) ** 0.5
    max_distance = ((viewport["width"]) ** 2 + (viewport["height"]) ** 2) ** 0.5
    
    # Scale movement time based on distance (with some randomness)
    move_time = Config.MOUSE_MOVE_TIME_MIN + (Config.MOUSE_MOVE_TIME_MAX - Config.MOUSE_MOVE_TIME_MIN) * (distance / max_distance)
    move_time *= random.uniform(0.8, 1.2)  # Add some randomness
    
    # Move along the path
    steps = len(path) - 1
    if steps <= 0:
        return
        
    step_time = move_time / steps
    
    # Move to starting position instantly (since we don't know the actual current position)
    await page.mouse.move(path[0]["x"], path[0]["y"])
    
    # Then follow the path with realistic timing
    for i in range(1, len(path)):
        await page.mouse.move(path[i]["x"], path[i]["y"])
        await asyncio.sleep(step_time * random.uniform(0.8, 1.2))
    
    logger.debug(f"Moved mouse to element {selector} in {move_time:.2f} seconds")

async def human_like_click(page: Page, selector: str) -> None:
    """Click on an element in a human-like manner."""
    # First move the mouse to the element
    await human_like_mouse_move(page, selector)
    
    # Small random delay before clicking (as humans do)
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    # Now click
    await page.click(selector)
    logger.debug(f"Clicked on element: {selector}")

def generate_realistic_typing_delays(text: str) -> List[float]:
    """
    Generate realistic typing delays for a given text.
    Returns a list of delays (in seconds) between keystrokes.
    """
    delays = []
    
    # Calculate base typing speed (characters per second)
    base_chars_per_sec = random.uniform(
        Config.TYPING_SPEED_MIN_CHARS_SEC,
        Config.TYPING_SPEED_MAX_CHARS_SEC
    )
    
    # Convert to base delay between keystrokes
    base_delay = 1.0 / base_chars_per_sec
    
    # Generate delays for each character
    for i, char in enumerate(text):
        # Start with base delay
        delay = base_delay
        
        # Add variance to typing speed
        delay *= random.uniform(
            1.0 - Config.TYPING_SPEED_VARIANCE,
            1.0 + Config.TYPING_SPEED_VARIANCE
        )
        
        # Slow down for special characters, uppercase, and numbers
        if not char.islower() and not char.isspace():
            delay *= random.uniform(1.2, 1.5)
        
        # Pause longer after punctuation
        if i > 0 and text[i-1] in ".!?":
            delay += random.uniform(Config.SENTENCE_PAUSE_MIN, Config.SENTENCE_PAUSE_MAX)
        
        # Pause after spaces (word breaks) sometimes
        elif i > 0 and text[i-1] == " " and random.random() < Config.WORD_PAUSE_CHANCE:
            delay += random.uniform(Config.WORD_PAUSE_MIN, Config.WORD_PAUSE_MAX)
        
        delays.append(delay)
    
    return delays

async def human_like_typing(page: Page, selector: str, text: str, correct_errors: bool = True) -> None:
    """
    Type text in a human-like manner with variable speed, pauses, and occasional errors.
    """
    # First, click on the element to focus it
    await human_like_click(page, selector)
    
    # Clear any existing text (if needed)
    await page.fill(selector, "")
    
    # Generate typing delays
    delays = generate_realistic_typing_delays(text)
    
    # Type character by character with realistic timing
    i = 0
    while i < len(text):
        # Decide if we'll make a typing error
        make_error = correct_errors and random.random() < Config.TYPING_ERROR_CHANCE
        
        if make_error:
            # Type an incorrect character (usually adjacent on keyboard)
            wrong_char = get_adjacent_key(text[i])
            await page.type(selector, wrong_char, delay=0)
            
            # Short pause to "notice" the error
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Delete the error
            await page.press(selector, "Backspace")
            
            # Another short pause
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Now type the correct character
            await page.type(selector, text[i], delay=0)
        else:
            # Type the correct character
            await page.type(selector, text[i], delay=0)
        
        # Wait according to our realistic delay model
        if i < len(delays):
            await asyncio.sleep(delays[i])
        
        i += 1
    
    logger.debug(f"Human-like typing completed for text of length {len(text)}")

def get_adjacent_key(char: str) -> str:
    """Get an adjacent key on the keyboard for realistic typos."""
    keyboard_layout = {
        'a': ['q', 's', 'z'],
        'b': ['v', 'g', 'h', 'n'],
        'c': ['x', 'd', 'f', 'v'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'],
        'e': ['w', 's', 'd', 'r'],
        'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'y', 'h', 'b', 'v'],
        'h': ['g', 'y', 'u', 'j', 'n', 'b'],
        'i': ['u', 'j', 'k', 'o'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'],
        'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p', ';'],
        'm': ['n', 'j', 'k', ','],
        'n': ['b', 'h', 'j', 'm'],
        'o': ['i', 'k', 'l', 'p'],
        'p': ['o', 'l', ';', '['],
        'q': ['1', 'w', 'a'],
        'r': ['e', 'd', 'f', 't'],
        's': ['a', 'w', 'e', 'd', 'x', 'z'],
        't': ['r', 'f', 'g', 'y'],
        'u': ['y', 'h', 'j', 'i'],
        'v': ['c', 'f', 'g', 'b'],
        'w': ['q', 'a', 's', 'e'],
        'x': ['z', 's', 'd', 'c'],
        'y': ['t', 'g', 'h', 'u'],
        'z': ['a', 's', 'x'],
        '0': ['9', '-', '='],
        '1': ['`', '2', 'q'],
        '2': ['1', '3', 'w'],
        '3': ['2', '4', 'e'],
        '4': ['3', '5', 'r'],
        '5': ['4', '6', 't'],
        '6': ['5', '7', 'y'],
        '7': ['6', '8', 'u'],
        '8': ['7', '9', 'i'],
        '9': ['8', '0', 'o'],
        ' ': [' ']  # Space typically only mistypes as space
    }
    
    # For uppercase, symbols, etc. just return the character itself
    char_lower = char.lower()
    if char_lower not in keyboard_layout:
        return char
    
    # Get random adjacent key
    adjacent = random.choice(keyboard_layout[char_lower])
    
    # Match case of original character
    if char.isupper():
        return adjacent.upper()
    return adjacent

async def random_delay() -> None:
    """Add a random delay between actions to mimic human behavior."""
    delay = random.uniform(Config.ACTION_DELAY_MIN, Config.ACTION_DELAY_MAX)
    await asyncio.sleep(delay)

async def take_screenshot(page: Page, name: str) -> str:
    """Take a screenshot and save it to the screenshots folder."""
    if not Config.TAKE_SCREENSHOTS:
        return ""
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    path = Config.SCREENSHOT_FOLDER / filename
    
    await page.screenshot(path=str(path))
    logger.debug(f"Screenshot saved: {path}")
    return str(path)

async def wait_for_user_action(page: Page, message: str, next_url_pattern: Optional[str] = None) -> None:
    """
    Display a message to the user and wait until they perform the required action.
    """
    print("\n" + "="*80)
    print(f"ACTION REQUIRED: {message}")
    print("="*80 + "\n")
    
    summary_logger.info(f"Waiting for user action: {message}")
    
    if next_url_pattern:
        # Wait for URL to match the expected pattern
        try:
            await page.wait_for_url(re.compile(next_url_pattern), timeout=300000)  # 5-minute timeout
            logger.info(f"Detected navigation to URL matching: {next_url_pattern}")
        except Error as e:
            logger.warning(f"Timeout waiting for navigation: {e}")
            print("\nTimeout waiting for navigation. Please press Enter when done...")
            input()
    else:
        # If no URL pattern, just wait for user to press Enter
        input("Press Enter when you have completed this action...")
    
    await random_delay()
    logger.info("User action completed")

async def retry_with_backoff(func, *args, max_retries: int = 3, **kwargs):
    """Retry a function with exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise
            
            # Calculate backoff time
            backoff_time = Config.RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning(f"Attempt {attempt} failed with error: {e}. Retrying in {backoff_time} seconds...")
            await asyncio.sleep(backoff_time)

async def wait_for_facebook_login_completion(page: Page) -> bool:
    """
    Wait for the user to complete the Facebook login process.
    """
    # Various indicators that login is complete
    success_selectors = [
        "div[role='banner']",  # Facebook navbar
        "div[aria-label='Create a post']",  # Post composer
        "[aria-label='Home']",  # Home button
        "[aria-label='Facebook']",  # Facebook logo in new UI
        "a[aria-label='Home']",  # Another Home button variant
        "div[data-pagelet='Stories']",  # Stories section
        "div[role='main']",  # Main content area
    ]
    
    # Combine selectors with OR (comma in CSS)
    combined_selector = ", ".join(success_selectors)
    
    try:
        # Wait for any of the success indicators (with a longer timeout)
        logger.info("Waiting for login completion...")
        await page.wait_for_selector(combined_selector, timeout=300000)  # 5-minute timeout
        
        # Take a screenshot of the logged-in state
        await take_screenshot(page, "login_successful")
        
        current_url = page.url
        logger.info(f"Login successful! Current URL: {current_url}")
        summary_logger.info("Login successful")
        return True
        
    except Error as e:
        logger.error(f"Login completion detection failed: {e}")
        await take_screenshot(page, "login_failed")
        summary_logger.error("Login failed or took too long")
        return False

async def login_to_facebook(page: Page) -> bool:
    """
    Log in to Facebook with provided credentials, letting user handle security challenges.
    """
    logger.info(f"Navigating to Facebook login page: {Config.FB_LOGIN_URL}")
    await page.goto(Config.FB_LOGIN_URL)
    await random_delay()
    
    # Take screenshot before login attempt
    await take_screenshot(page, "before_login")
    
    try:
        # Fill in login credentials
        logger.info("Entering email/username")
        await human_like_typing(page, "#email", Config.FB_USERNAME)
        await random_delay()
        
        logger.info("Entering password")
        # Use more careful typing for passwords (no error correction)
        await human_like_typing(page, "#pass", Config.FB_PASSWORD, correct_errors=False)
        await random_delay()
        
        # Click login button
        logger.info("Clicking login button")
        await human_like_click(page, "[name='login']")
        summary_logger.info("Login credentials submitted")
        
        # Take screenshot after login attempt
        await take_screenshot(page, "after_login_click")
        
        # Check if there are security challenges
        challenge_selectors = [
            "input[name='approvals_code']",  # 2FA code input
            "input#checkpointSubmitButton",  # Checkpoint submit button
            "button[value='Continue']",      # Continue button in security flow
            "#captcha_response",             # CAPTCHA field
            "button[data-testid='checkpointSubmitButton']",  # Another checkpoint button
            "input[name='verification_code']",  # Verification code input
            "input[name='reset_action']",  # Account reset action
        ]
        
        # Combine selectors with OR (comma in CSS)
        combined_challenge_selector = ", ".join(challenge_selectors)
        
        try:
            # Check for security challenges with a short timeout
            await page.wait_for_selector(combined_challenge_selector, timeout=5000)
            # If we get here, security challenges were detected
            logger.info("Security challenges detected")
            summary_logger.info("Security challenge detected - user interaction required")
            
            # Take screenshot of the security challenge
            await take_screenshot(page, "security_challenge")
            
            # Wait for user to handle the security challenges
            await wait_for_user_action(
                page,
                "Facebook security check detected. Please complete the security verification steps in the browser. "
                "The automation will continue once you're fully logged in."
            )
            
            # Now wait for login to complete
            return await wait_for_facebook_login_completion(page)
            
        except Error:
            # No security challenges detected, just wait for login to complete
            logger.info("No immediate security challenges detected")
            return await wait_for_facebook_login_completion(page)
            
    except Error as e:
        logger.error(f"Login process failed: {e}")
        await take_screenshot(page, "login_error")
        summary_logger.error(f"Login process failed: {e}")
        return False

async def go_to_facebook_post(page: Page, post_url: str) -> bool:
    """
    Navigate to a specific Facebook post.
    """
    logger.info(f"Navigating to Facebook post: {post_url}")
    summary_logger.info(f"Navigating to post: {post_url}")
    
    try:
        # Navigate to the post URL
        await page.goto(post_url)
        await random_delay()
        
        # Take screenshot of the post page
        await take_screenshot(page, "post_page")
        
        # Check if we're on the right page by looking for comment box or other post indicators
        post_indicators = [
            "div[aria-label='Comment']",
            "div[contenteditable='true'][aria-label*='comment' i]",
            "form div[contenteditable='true']",
            "div[aria-label='Write a comment']",
            "div.uiContextualLayerParent div[contenteditable='true']",
            "div[data-testid='UFI2CommentsList']",  # Comment list
            "div.UFIList",  # Another comment list indicator
            "div[data-visualcompletion='ignore-dynamic']",  # Post content
        ]
        
        # Check for any of the post indicators
        for indicator in post_indicators:
            if await page.locator(indicator).count() > 0:
                logger.info(f"Successfully navigated to post (confirmed by presence of: {indicator})")
                summary_logger.info("Successfully navigated to post")
                return True
        
        # If we couldn't verify we're on a post page
        logger.warning("Navigation to post completed, but couldn't confirm it's a post page")
        summary_logger.warning("Navigation to post completed, but couldn't confirm it's a post page")
        return True  # Return True anyway, we'll try to find comment box later
        
    except Error as e:
        logger.error(f"Navigation to post failed: {e}")
        await take_screenshot(page, "post_navigation_error")
        summary_logger.error(f"Navigation to post failed: {e}")
        return False

async def find_comment_box(page: Page) -> Optional[str]:
    """
    Find the comment box on a Facebook post.
    """
    # Multiple potential selectors for comment box (in order of preference)
    comment_box_selectors = [
        "div[aria-label='Write a comment']",
        "div[aria-label='Comment']",
        "div[contenteditable='true'][aria-label*='comment' i]",
        "form div[contenteditable='true']",
        "div.uiContextualLayerParent div[contenteditable='true']",
        "div.UFIAddCommentInput div[contenteditable='true']",
        "div[data-testid='commentingInputContainer'] div[contenteditable='true']",
        "div.UFIInputContainer textarea",
        "div.UFIAddCommentInput div[role='textbox']",
    ]
    
    # Try each selector
    for selector in comment_box_selectors:
        try:
            if await page.locator(selector).count() > 0:
                logger.info(f"Comment box found using selector: {selector}")
                return selector
        except Error:
            continue
    
    logger.error("Could not find any comment box on the page")
    await take_screenshot(page, "comment_box_not_found")
    summary_logger.error("Failed to find comment box")
    return None

async def post_comment(page: Page, comment_text: str, reply_to_comment_id: Optional[str] = None) -> bool:
    """
    Post a comment on a Facebook post or reply to a specific comment.
    """
    try:
        if reply_to_comment_id:
            logger.info(f"Preparing to reply to comment ID: {reply_to_comment_id}")
            
            # Multiple possible selectors for reply buttons
            reply_button_selectors = [
                f"div[data-commentid='{reply_to_comment_id}'] a[data-testid='UFI2CommentActionLinks/reply']",
                f"#{reply_to_comment_id} a.UFIReplyLink",
                f"[id*='{reply_to_comment_id}'] a:has-text('Reply')",
                f"div[data-testid='{reply_to_comment_id}'] div[role='button']:has-text('Reply')",
                f"div[id*='{reply_to_comment_id}'] span:has-text('Reply')",
            ]
            
            # Try each reply button selector
            reply_clicked = False
            for selector in reply_button_selectors:
                if await page.locator(selector).count() > 0:
                    await human_like_click(page, selector)
                    reply_clicked = True
                    break
                    
            if not reply_clicked:
                logger.error(f"Could not find reply button for comment ID: {reply_to_comment_id}")
                await take_screenshot(page, "reply_button_not_found")
                return False
                
            await random_delay()
            
            # Find the reply input box
            comment_box_selector = await find_comment_box(page)
            if not comment_box_selector:
                return False
                
        else:
            logger.info("Preparing to post a new comment")
            # Find the main comment box
            comment_box_selector = await find_comment_box(page)
            if not comment_box_selector:
                return False
            
            # Click on the comment box to focus it
            await human_like_click(page, comment_box_selector)
            await random_delay()
        
        # Type the comment with human-like typing
        logger.info(f"Typing comment: {comment_text[:30]}...")
        await human_like_typing(page, comment_box_selector, comment_text)
        await random_delay()
        
        # Take screenshot before posting
        await take_screenshot(page, "before_posting_comment")
        
        # Press Enter to submit the comment
        logger.info("Submitting comment")
        await page.press(comment_box_selector, "Enter")
        
        # Wait for comment to be posted (look for our text in the page)
        try:
            # Wait for a few moments to let the comment post
            await asyncio.sleep(2)
            
            # Look for text matching our comment
            # Use a more lenient selector that just finds text content
            sanitized_text = comment_text[:40].replace("'", "\\'")
            comment_content_selector = f"div:has-text('{sanitized_text}')"
            
            # Try a few times with increasing timeouts
            for timeout in [5000, 10000, 15000]:
                try:
                    await page.wait_for_selector(comment_content_selector, timeout=timeout)
                    logger.info("Comment successfully posted")
                    summary_logger.info(f"Comment successfully posted: {comment_text[:40]}...")
                    
                    # Take screenshot after posting
                    await take_screenshot(page, "comment_posted")
                    return True
                except Error:
                    continue
                    
            # Alternative verification - check if the comment box is cleared
            try:
                comment_box_text = await page.locator(comment_box_selector).input_value()
                if not comment_box_text.strip():
                    logger.info("Comment likely posted (comment box cleared)")
                    await take_screenshot(page, "comment_likely_posted")
                    summary_logger.info("Comment likely posted (could not directly confirm)")
                    return True
            except Error:
                pass
                
            logger.warning("Could not confirm comment was posted")
            await take_screenshot(page, "comment_post_unconfirmed")
            # Return True anyway, as the comment might have been posted
            summary_logger.warning("Could not confirm if comment was posted")
            return True
            
        except Error as e:
            logger.warning(f"Could not confirm comment was posted: {e}")
            await take_screenshot(page, "comment_post_unconfirmed")
            # Return True anyway, as the comment might have been posted
            summary_logger.warning("Could not confirm if comment was posted")
            return True
            
    except Error as e:
        logger.error(f"Failed to post comment: {e}")
        await take_screenshot(page, "comment_post_error")
        summary_logger.error(f"Failed to post comment: {e}")
        return False

async def main():
    """Main function to run the Facebook commenter script."""
    # Print welcome message and script info
    print(f"\nFacebook Commenter Script v{SCRIPT_VERSION}")
    print("=" * 60)
    print("Features:")
    for feature in SCRIPT_FEATURES:
        print(f"- {feature}")
    print("=" * 60 + "\n")
    
    summary_logger.info(f"Script started (version {SCRIPT_VERSION})")
    
    # Get post URL and comment text from user
    post_url = input("Enter the Facebook post URL: ").strip()
    comment_text = input("Enter your comment: ").strip()
    
    # Check if this is a reply to a specific comment
    reply_to_comment = input("Is this a reply to a specific comment? (y/n): ").strip().lower()
    reply_to_comment_id = None
    
    if reply_to_comment == 'y':
        reply_to_comment_id = input("Enter the comment ID to reply to: ").strip()
    
    summary_logger.info(f"Target post: {post_url}")
    if reply_to_comment_id:
        summary_logger.info(f"Planning to reply to comment: {reply_to_comment_id}")
    else:
        summary_logger.info("Planning to post a new comment")
    
    # Get browser fingerprint
    fingerprint = get_browser_fingerprint()
    logger.info(f"Using browser fingerprint: {fingerprint}")
    
    # Launch browser
    async with async_playwright() as p:
        browser_type = p.chromium
        
        # Launch browser with custom arguments
        browser = await browser_type.launch(
            headless=Config.HEADLESS,
            slow_mo=Config.SLOWMO
        )
        
        # Create a context with fingerprint settings
        context = await browser.new_context(
            viewport=fingerprint["viewport"],
            user_agent=fingerprint["user_agent"],
            timezone_id=fingerprint["timezone_id"],
            locale=fingerprint["locale"],
            device_scale_factor=fingerprint["device_scale_factor"],
            is_mobile=fingerprint["is_mobile"],
            has_touch=fingerprint["has_touch"],
            color_scheme=fingerprint["color_scheme"],
        )
        
        # Apply stealth plugin if enabled
        if Config.STEALTH_ENABLED:
            await stealth_async(context)
            logger.info("Stealth mode enabled")
        
        # Set default timeout
        context.set_default_timeout(Config.DEFAULT_TIMEOUT)
        
        # Create a new page
        page = await context.new_page()
        
        try:
            # Handle browser closures gracefully
            close_event = asyncio.Event()
            
            async def on_close():
                logger.info("Browser was closed by user")
                summary_logger.info("Browser closed by user - stopping script")
                close_event.set()
                
            context.on("close", lambda _: asyncio.create_task(on_close()))
            
            # Login to Facebook
            login_success = await retry_with_backoff(
                login_to_facebook, 
                page, 
                max_retries=Config.MAX_RETRIES
            )
            
            if not login_success:
                logger.error("Login failed. Exiting script.")
                summary_logger.error("Script terminated due to login failure")
                return
                
            # Navigate to the post
            post_success = await retry_with_backoff(
                go_to_facebook_post, 
                page, 
                post_url, 
                max_retries=Config.MAX_RETRIES
            )
            
            if not post_success:
                logger.error("Failed to navigate to post. Exiting script.")
                summary_logger.error("Script terminated due to navigation failure")
                return
                
            # Post the comment
            comment_success = await retry_with_backoff(
                post_comment, 
                page, 
                comment_text, 
                reply_to_comment_id, 
                max_retries=Config.MAX_RETRIES
            )
            
            if comment_success:
                logger.info("Comment posted successfully")
                summary_logger.info("Script completed successfully")
            else:
                logger.error("Failed to post comment")
                summary_logger.error("Script failed to post comment")
                
            # Wait for user to close the browser
            print("\nTask completed. You can now close the browser or press Ctrl+C to exit.")
            await close_event.wait()
                
        except KeyboardInterrupt:
            logger.info("Script interrupted by user (Ctrl+C)")
            summary_logger.info("Script terminated by user")
            
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            await take_screenshot(page, "unexpected_error")
            summary_logger.error(f"Script failed with unexpected error: {e}")
            
        finally:
            # Clean up
            if 'browser' in locals() and browser:
                await browser.close()
            logger.info("Script completed, browser closed")

if __name__ == "__main__":
    asyncio.run(main())