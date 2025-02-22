PROXY = True
PROXY_OTP = True

"""
The test verifies if the 'removed' message on the LHN is translated to Spanish after removing a member from a group chat.
"""

import pytest
from playwright.async_api import expect

from utils.login import sign_in, complete_onboarding
from utils.browser import start_browser, close_browser
from utils.email_handler import get_unique_derived_email

# Email
BASE_EMAIL = "testerfreelancer555@gmail.com"
PASSWORD = "snct ajbr yadx kwlq"

@pytest.mark.asyncio
async def test_remove_member_message():
    proxy = {"server":  "http://127.0.0.1:8080/"} if PROXY else None
    launch_args=[
    "--ignore-certificate-errors",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process"
    ]
    context, page, playwright = await start_browser(launch_args=launch_args, slow_mo=1000, proxy=proxy)
    try:
        # Log in the user
        # email = get_unique_derived_email(email=BASE_EMAIL)
        email = "testerfreelancer555+1740060296@gmail.com"
        await sign_in(page, email=email, password=PASSWORD, mock_otp=PROXY_OTP)
        # await complete_onboarding(page, "Test", "User")
        # Changing the language to Spanish
        await page.get_by_label("My settings").click()
        await page.get_by_text("Preferences").click()
        await page.get_by_text("Language").click()
        await page.get_by_label("Spanish").click()
        # Creating a group chat
        await page.get_by_label("Recibidos").click()
        await page.get_by_label("Iniciar chat (Acción flotante)").click()
        await page.get_by_text("Iniciar chat").click()
        await page.get_by_test_id("selection-list-text-input").fill("testerfreelancer555@gmail.com")
        await page.get_by_role("button", name="Añadir al grupo").click()
        await page.get_by_test_id("selection-list-text-input").click()
        await page.get_by_test_id("selection-list-text-input").fill("testerfreelancer555+1@gmail.com")
        await page.get_by_role("button", name="Añadir al grupo").click()
        await page.get_by_role("button", name="Siguiente").click()
        await page.get_by_role("button", name="Crear grupo").click()
        await page.get_by_label("Test, Test, Test_1").click()
        # Remove someone from the group chat
        await page.get_by_text("Miembros").click()
        await page.get_by_label("Test User").nth(1).click()
        await page.get_by_role("button", name="seleccionado").click()
        await page.get_by_text("Eliminar miembro").click()
        await page.get_by_role("button", name="Eliminar").click()
        await page.get_by_test_id("ReportParticipantsPage").get_by_label("Volver").click()
        await page.get_by_label("Volver").click()
        # Assert the text on LHN
        await expect(page.get_by_label("Vista previa del último").last).to_contain_text("eliminó")
        await expect(page.get_by_text("removed")).not_to_be_visible()

    finally:
        await close_browser(context, page, playwright)
