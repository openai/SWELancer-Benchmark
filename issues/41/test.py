from playwright.sync_api import sync_playwright, expect

def test_53980():
    with sync_playwright() as p:
        browser = p.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 1000, channel = "chromium")
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.goto("https://dev.new.expensify.com:8082/")
        page.get_by_test_id("username").fill("totherandomuser@gmail.com")
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_text("Please enter the magic code")).to_be_visible()
        page.evaluate("Onyx.merge('account', {smsDeliveryFailureStatus: {}});")
        expect(page.get_by_text("We've been unable to deliver")).to_be_visible()
        page.get_by_label("Go back").click()
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_text("Please enter the magic code")).to_be_visible()
        page.evaluate("Onyx.merge('account', {smsDeliveryFailureStatus: {}});")
        page.get_by_role("button", name="Validate").click()
        page.evaluate("""
        Onyx.merge("account", {
            smsDeliveryFailureStatus: {
                isReset: true,
                hasSMSDeliveryFailure: true,
                message: "Please wait 23 hours and 37 minutes before trying again."
            }
        });
    """)
        expect(page.get_by_text("Validation failed because it hasn’t been 24 hours since your last attempt. Please wait 23 hours and 37 minutes before trying again.")).to_be_visible()
        page.get_by_role("button", name="Got it").click()
        expect(page.get_by_text("Get started below.")).to_be_visible()
        page.reload()
        page.get_by_test_id("username").fill("totherandomuser@gmail.com")
        page.get_by_role("button", name="Continue").click()
        expect(page.get_by_text("Please enter the magic code")).to_be_visible(timeout=1000)
        page.evaluate("Onyx.merge('account', {smsDeliveryFailureStatus: {}});")
        page.get_by_role("button", name="Validate").click()
        page.evaluate("""Onyx.merge("account", {smsDeliveryFailureStatus: {isReset: true,hasSMSDeliveryFailure: false}});""")
        expect(page.get_by_text("Your number has been validated! Click below to send a new magic sign-in code.")).to_be_visible()
        page.get_by_role("button", name="Send").click()
        page.on("request", lambda request: print(request.url) if "BeginSignIn" in request.url else None)
        page.evaluate("""Onyx.merge("account", {smsDeliveryFailureStatus: null});""")
        expect(page.get_by_text("Please enter the magic code")).to_be_visible()
                
        browser.close()