import pytest_asyncio
import pytest
from moviepy import VideoClip
import numpy as np
from PIL import Image, ImageDraw
import io
import tempfile
import os
import re

from playwright.async_api import async_playwright, expect
from utils.login import EmailHandler, complete_onboarding

NEWDOT_URL = "http://dev.new.expensify.com:8082/"
EXPENSIFY_EMAIL = "testingq186+52114@gmail.com"
EXPENSIFY_PASSWORD = "kkfr hqiv yuxq rbso"

TESTING_FLOW = True

@pytest_asyncio.fixture
async def page():
    """
    Launch the Expensify app.
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        proxy={"server": "http://localhost:8080"},
        slow_mo=500
    )

    context = await browser.new_context(ignore_https_errors=True,viewport={'width': 400, 'height': 600})
    page = await context.new_page()

    yield page
    await browser.close()
    await pw.stop()

async def create_video():
    """
    Create a WebM video using moviepy, save it temporarily, and return it as a BytesIO buffer.
    """
    def make_frame(t):
        """Generate a frame for the video at time `t`."""
        frame_index = int(t * 30)  # Assuming 30 FPS
        img = Image.new("RGB", (640, 480), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle((50, 50, 590, 430), outline="red", width=5)
        draw.text((240, 220), f"Frame {frame_index + 1}", fill="blue")
        return np.array(img)

    # Create the video clip using moviepy
    video_clip = VideoClip(make_frame, duration=5)  # 5-second video

    # Create a temporary file to store the WebM video
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_video_file:
        temp_file_path = temp_video_file.name
        video_clip.write_videofile(temp_file_path, codec="libvpx", fps=30, preset="ultrafast", audio=False)

    # Read the temporary file into a BytesIO buffer
    video_buffer = io.BytesIO()
    with open(temp_file_path, "rb") as f:
        video_buffer.write(f.read())

    # Ensure cleanup by removing the temporary file
    os.remove(temp_file_path)
    video_buffer.seek(0)
    return video_buffer

async def new_dot_login(page, email, password):
    await page.goto(NEWDOT_URL)
    with EmailHandler(email, password) as email_handler:
        if not TESTING_FLOW :
            email_handler.clean_inbox()  # Clean inbox

        # Enter email
        await page.get_by_role("textbox", name="Phone or email").fill(email)
        await page.get_by_role("button", name="Continue").click()
        
        try:
            await expect(page.locator('input[name="validateCode"]').first).to_be_visible()
            otp = email_handler.read_otp_code() if not TESTING_FLOW else "123456"
            await page.locator('input[name="validateCode"]').first.fill(otp)
            # Wait sign in to complete
            await page.get_by_text("Please enter the magic code").wait_for(state="hidden")
        except Exception:
            await page.get_by_role("button", name="Join").click()
            await complete_onboarding(page, "Testing", "52114")

@pytest.mark.asyncio
async def test_scrollable_playback_speeds(page):
    await new_dot_login(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)

    try:
        # Need to press back for sign up
        await page.get_by_label("Back").click(timeout=5000)
    except Exception:
        pass
    await page.get_by_label("Navigates to a chat").get_by_text("Testing 52114 (you)").click(timeout=10_000)
    await page.get_by_label("Create").last.click()
    async with page.expect_file_chooser() as fc:
        await page.get_by_label("Add attachment").click()
    file_chooser = await fc.value

    video_buffer = await create_video()
    await file_chooser.set_files({
      "name": "test.webm",
      "mimeType": "video/webm",
      "buffer": video_buffer.getvalue()
    })
    await page.get_by_role("dialog").get_by_role("button", name="Send").click()
    
    # Click the video
    await page.wait_for_timeout(3000)
    await page.get_by_label(re.compile(r".*\.webm$")).first.click()
    await page.get_by_role("dialog").get_by_role("button").last.hover()
    await page.get_by_label("More").click()
    await page.get_by_label("Playback speed").click()
    await page.mouse.wheel(0, 200)

    await expect(page.get_by_label("1.25", exact=True)).to_be_in_viewport()
    await expect(page.get_by_label("1.5", exact=True)).to_be_in_viewport()
    await expect(page.get_by_label("1.75", exact=True)).to_be_in_viewport()
    await expect(page.get_by_label("2", exact=True)).to_be_in_viewport()
