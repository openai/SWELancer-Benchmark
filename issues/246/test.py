import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

"""
Test to verify that GL codes are saved for dependent tags
"""

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, expect, Page
from utils.email_handler import EmailHandler

NEW_DOT_URL = "https://dev.new.expensify.com:8082"

EXPENSIFY_EMAIL = "testingq186+45771_1@gmail.com"
EXPENSIFY_PASSWORD = ""

TESTING_FLOW = True

@pytest_asyncio.fixture
async def page():
  pw = await async_playwright().start()
  browser = await pw.chromium.launch(channel="chrome", headless=True, args=["--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process" ], proxy={"server": "http://localhost:8080"}, slow_mo=500)
  page = await browser.new_page()
  
  yield page

  await page.close()
  await browser.close()
  await pw.stop()

async def sign_in_new_dot(page: Page, email: str, password: str):
  with EmailHandler(email, password) as email_handler:
    if not TESTING_FLOW:
      email_handler.clean_inbox()

    await page.get_by_test_id("username").fill(email)
    await page.get_by_role("button", name="Continue").click()
    await expect(page.get_by_test_id("validateCode")).to_be_visible()
    otp = email_handler.read_otp_code() if not TESTING_FLOW else "123456"
    await page.get_by_test_id("validateCode").fill(otp)

@pytest.mark.asyncio
async def test_saving_GL_code_for_dependent_tags(page: Page):
  await page.goto(NEW_DOT_URL)
  await page.wait_for_load_state("load")

  await sign_in_new_dot(page, EXPENSIFY_EMAIL, EXPENSIFY_PASSWORD)
  
  await page.get_by_label("My settings").click()
  await page.get_by_test_id("InitialSettingsPage").get_by_label("Workspaces").get_by_text("Workspaces").click()
  await page.get_by_label("row").get_by_text(EXPENSIFY_EMAIL.split("@")[0], exact=True).click()

  try:
      await expect(page.get_by_label("Tags")).to_be_visible()
  except:
      await page.get_by_label("More features").click()
      await page.get_by_label("Classify costs and track").click()

  await page.get_by_label("Tags").click()

  await page.get_by_label("State").click()
  await page.locator("#California").click()

  await page.get_by_role("menuitem", name="GL code").click()
  await page.get_by_role("textbox", name="GL code").clear()
  await page.get_by_role("textbox", name="GL code").fill("This GL code should be visible")
  await page.get_by_role("button", name="Save").click()


  await expect(page.get_by_test_id("TagSettingsPage").get_by_text("This GL code should be visible")).to_be_visible()
  


  await page.get_by_role("menuitem", name="GL code").click()
  await page.get_by_role("textbox", name="GL code").clear()
  await page.get_by_role("button", name="Save").click()