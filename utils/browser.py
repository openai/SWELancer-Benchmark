import logging
from playwright.async_api import async_playwright
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up browser
async def start_browser(headless=False, persistent=False, data_dir=None, launch_args=None, slow_mo=None, **kwargs):
    """
    Start a browser instance with the given parameters.

    :param headless: Boolean to specify if the browser should run in headless mode.
    :param persistent: Boolean to specify if the browser context should be persistent.
    :param data_dir: Directory to store browser data for persistent context.
    :param launch_args: List of arguments to pass to the browser instance.
    :param slow_mo: Slow down the browser operations by the specified amount of milliseconds.
    :return: A tuple of (context, page, playwright).
    """
    # Override provided launch arguments and set proxy
    launch_args = [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--ignore-certificate-errors"
    ]
    proxy = {"server": "http://localhost:8080"}
    persistent = False

    # Initialize Playwright
    playwright = await async_playwright().start()
    context, page = None, None
    if persistent:
        if data_dir is None:
            data_dir = 'browser_context'
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        context = await playwright.chromium.launch_persistent_context(
            data_dir,
            headless=headless,
            args=launch_args,
            slow_mo=slow_mo,
            proxy=proxy
        )
        page = context.pages[0]
    else:
        browser = await playwright.chromium.launch(headless=headless, args=launch_args, slow_mo=slow_mo, proxy=proxy)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
    
    logging.info("The browser has been started.")

    return context, page, playwright  # Return playwright to close later


# Function to reset browser
async def close_browser(context, page, playwright):
    await page.close()
    await context.close()
    await playwright.stop()  # Explicitly stop Playwright
    logging.info("The browser has been stopped.")