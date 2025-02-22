from playwright.sync_api import sync_playwright, expect

def generate_random_email():
    return f"nitish.expensify+345687645@gmail.com"


def login_user(pw):
    browser = pw.chromium.launch(proxy = {"server": "http://localhost:8080"}, headless = False, args = ["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors", "--disable-web-security", "--disable-features=IsolateOrigins,site-per-process"], slow_mo = 30, channel = "chromium")
    context_args = {}
    context_args["timezone_id"] = "Asia/Calcutta"
    context = browser.new_context(**context_args)
    page = context.new_page()
    user_email = generate_random_email()

    page.goto('https://dev.new.expensify.com:8082/', timeout=3000000)

    page.locator('input[type="email"]').fill(user_email)
    page.get_by_role("button", name="Continue").click()

    try:
        expect(page.get_by_role("button", name="Sign in")
               ).to_be_visible(timeout=3000)
        page.get_by_test_id("validateCode").fill("123456")
    except Exception:
        page.get_by_role("button", name="Join").click()

    return page, browser


def test_the_issue():
    with sync_playwright() as p:
        page, browser = login_user(p)
        page.get_by_test_id("CustomBottomTabNavigator").get_by_label(
            "Search").click(timeout=30000)
        page.wait_for_timeout(10000)
        flicker_detected = False
        try:
            is_flicker_detected = page.wait_for_function("""
                () => {
                    return new Promise(resolve => {
                        const allButtons = document.querySelectorAll('button');

                        for (const btn of allButtons) {
                            if (btn.innerText.trim() === "From") {
                                btn.closest('button').click();
                                break;
                            }
                        }
                        const checkText = () => {
                            const element = document.querySelector('div[data-testid="selection-list"] > div > div:nth-child(2)');
                            if (element && element.innerText.includes("zxc")) {
                                resolve(true);
                            } else {
                                requestAnimationFrame(checkText);
                            }
                        };
                        checkText();
                    });
                }
            """, timeout=20000)
            flicker_detected = is_flicker_detected
        except Exception:
            pass

        assert not flicker_detected, "The expenses change positions briefly after changing sorting order"

        browser.close()
