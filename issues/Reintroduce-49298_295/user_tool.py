import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Verify whether the intro text on private notes list scrolls with the page.

"""

import os
import pytest
from playwright.async_api import Page, expect, async_playwright
from utils.login import NEW_DOT_URL, sign_in
from utils.browser import close_browser
from utils.trace_cleaner import trace_cleaner

STATIC_PREFIX = "49298_2p1"
EXPENSIFY_USERNAME_FIRSTNAME = "new"
EXPENSIFY_USERNAME_LASTNAME = "user"
EXPENSIFY_USERNAME = f"{EXPENSIFY_USERNAME_FIRSTNAME} {EXPENSIFY_USERNAME_LASTNAME}"
EXPENSIFY_EMAIL_USERNAME = "osaidtest5"
EXPENSIFY_EMAIL = f"osaidtest5+{STATIC_PREFIX}@gmail.com"
EXPENSIFY_SECOND_USER_EMAIL = "osaidtest5+49337_2P1@gmail.com"
EXPENSIFY_PASSWORD = "ntvd acej mmaa qqmd"
DATA_DIR = "browser_context"
WORKSPACE_NAME = "workspace1"
SLOW_MO = 1000
NORMAL_RUN = False
GROUP_NAME = "new, osaidtest"

PRIVATE_NOTES_PLACEHOLDER = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Nam ac est semper, sodales odio vitae, interdum nunc.
Vestibulum tristique enim id velit vulputate fringilla.
Morbi vel ligula mollis lorem vehicula laoreet.

Phasellus id ipsum vel tellus elementum bibendum ut ac purus.

Vestibulum scelerisque nisi viverra, fringilla nisi quis, ultrices dui.
Praesent et leo in mi viverra hendrerit quis hendrerit nisl.
Sed varius tellus eget sapien molestie, at commodo turpis rhoncus.

Donec faucibus tortor vitae tincidunt consectetur.
Duis laoreet enim a metus facilisis, eu semper leo consequat.
Etiam porttitor lacus molestie massa bibendum ultricies.
Nulla a massa sit amet eros vulputate sollicitudin at vel purus.

Donec imperdiet elit vitae posuere ultricies.
Sed rhoncus mauris sed urna iaculis, in viverra augue fermentum.
Morbi eget felis quis sem ultricies sagittis.
Integer elementum dolor aliquam erat sollicitudin, id congue nisi luctus.
Duis ullamcorper nisl ullamcorper dignissim laoreet.

Sed eget dui nec nisi iaculis finibus non ac lectus.
Curabitur tempus leo in elit malesuada, nec commodo turpis rhoncus.
Vivamus pharetra risus sed risus commodo, vitae consectetur elit sagittis.

Vivamus elementum urna a congue viverra.
Sed volutpat libero et neque dignissim consequat.
Vivamus laoreet diam interdum, tincidunt ipsum at, luctus eros.
Suspendisse congue tellus at lacinia scelerisque.
Aliquam non lectus viverra, vulputate dolor nec, luctus justo.
Fusce eu purus interdum mauris tempus congue vel nec enim.

Aenean quis tellus a quam tincidunt dapibus nec id neque.
Aenean condimentum sem at fermentum rutrum.
Ut eget mi ullamcorper, lacinia mi nec, elementum nunc.
Nullam ac ex posuere, tincidunt ante eu, rhoncus odio.

Morbi ac ante in mauris hendrerit mattis.
Etiam varius ipsum nec est sollicitudin egestas.

Aliquam efficitur mi sed lorem consequat, vitae hendrerit tortor pharetra.
Vestibulum ornare nisi quis nisi mollis, vitae tincidunt ante elementum.
Donec in erat non justo accumsan cursus.
Nam non purus ut justo sollicitudin consectetur sed ac ex.
Vivamus eget nisl eget tortor porttitor ornare.
Mauris ut nisi vitae mauris placerat vestibulum.

Donec eu lectus porta, fringilla arcu nec, eleifend nisi.
Suspendisse malesuada enim vel eros eleifend, vel ultricies velit interdum.
Nullam lobortis lorem ut tristique commodo.
Morbi egestas tellus id dolor sagittis condimentum.
Nulla efficitur ligula feugiat libero laoreet, ullamcorper hendrerit sem suscipit.

Suspendisse accumsan orci quis lacinia pretium.
Vestibulum feugiat mauris a commodo pharetra.
Maecenas eleifend leo interdum metus aliquet cursus.
Fusce sed ante eget eros posuere sodales.

Praesent ac nisi vitae erat laoreet sagittis.
Praesent maximus magna eget metus vulputate, viverra convallis neque convallis.
Aliquam venenatis lectus non ante porttitor, eget rhoncus tellus lobortis.'''

PRIVATE_NOTES_INTRO_TEXT = "Keep notes about this chat here. You're the only person who can add, edit, or view these notes."

async def start_browser(
    headless=True,
    persistent=False,
    data_dir=None,
    slow_mo=500,
    launch_args=["--ignore-certificate-errors"],
):
    """
    Start a browser instance with the given parameters.

    :param headless: Boolean to specify if the browser should run in headless mode.
    :param persistent: Boolean to specify if the browser context should be persistent.
    :param data_dir: Directory to store browser data for persistent context.
    :return: A tuple of (context, page, playwright).
    """

    # Initialize Playwright
    playwright = await async_playwright().start()
    context, page = None, None
    if persistent:
        if data_dir is None:
            data_dir = "browser_context"
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        context = await playwright.chromium.launch_persistent_context(
            data_dir,
            headless=headless,
            args=launch_args,
            slow_mo=slow_mo,
            timezone_id="Asia/Karachi",
        )
        page = context.pages[0]
    else:
        browser = await playwright.chromium.launch(
            headless=headless, args=launch_args, slow_mo=slow_mo
        )
        context = await browser.new_context(
            ignore_https_errors=True, timezone_id="Asia/Karachi"
        )
        page = await context.new_page()

    return context, page, playwright  # Return playwright to close later


async def sign_in_recorded(page: Page, email: str):
    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()
    await page.get_by_test_id("validateCode").fill("123456")


@pytest.mark.asyncio
async def test_scrollview_in_private_notes():
    context, page, playwright = await start_browser(
        persistent=False,
        data_dir=DATA_DIR,
        headless=True,
        slow_mo=SLOW_MO,
        launch_args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
    )

    # Start tracing
    await context.tracing.start(
        title="test_scrollview_in_private_notes",
        snapshots=True,
        screenshots=True
    )

    try:
        # Step 1: Sign in
        if NORMAL_RUN:
            # Normal test run
            await sign_in(page, EXPENSIFY_EMAIL, password=EXPENSIFY_PASSWORD)
        else:
            # Recorded Test Run.
            await page.goto(NEW_DOT_URL)
            await sign_in_recorded(page=page, email=EXPENSIFY_EMAIL)

        # Create a new group chat.
        await page.get_by_label("Start chat (Floating action)").click()
        await page.get_by_label("Start chat", exact=True).click()
        await page.get_by_test_id("selection-list-text-input").fill(EXPENSIFY_SECOND_USER_EMAIL)
        await page.get_by_role("button", name="Add to group").click()
        await page.get_by_role("button", name="Next").click()
        await page.get_by_role("button", name="Start group").click()

        # Open Group Settings page.
        await page.get_by_label(GROUP_NAME).click()

        # Open Private Notes Editor Modal.
        await page.get_by_label("Private notes").click()

        # Save/Edit Dummy private notes (We need enough content to enable scrolling behavior)
        await page.get_by_role("textbox", name="Private notes").fill(PRIVATE_NOTES_PLACEHOLDER)
        await page.get_by_role("button", name="Save").click()

        # Reopen Private Notes Modal.
        await page.get_by_label("Private notes").click()

        # Scroll to the bottom of the viewport.
        await page.get_by_test_id("PrivateNotesListPage").get_by_test_id("comment").locator("div").hover()
        await page.mouse.wheel(0, 1000)

        # Assertion step, intro text should disappear from viewport upon scrolling.
        await expect(page.get_by_text(PRIVATE_NOTES_INTRO_TEXT)).not_to_be_in_viewport()
    except Exception as e:
        # Reraise after we ensure the trace is still saved
        raise e
    finally:
        # Stop tracing and export
        await context.tracing.stop()
        await context.tracing.export(path="/app/expensify/user_tool/output_browser1.zip")
        trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
        # Close the browser
        await close_browser(context, page, playwright)
