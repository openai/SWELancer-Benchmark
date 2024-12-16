import sys, os

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, base_path)

import time
from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner


# Utility to generate a random email and random work name
def generate_random_email():
    timestamp = int(time.time())
    return f"t56826807+{timestamp}@gmail.com"


def generate_random_work_name():
    timestamp = int(time.time())
    return f"Work_{timestamp}"


def login(p, email, first_name, last_name, work_name=None):
    browser = p.chromium.launch(headless=True, slow_mo=500, args=[
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
    ])
    # Create context and start tracing for this browser
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)

    page = context.new_page()
    page.goto("https://dev.new.expensify.com:8082/")
    page.locator('input[type="email"]').fill(email)
    page.locator("button", has_text="Continue").click()

    try:
        page.locator("button", has_text="Join").click()
    except Exception:
        pass

    if work_name:
        page.locator("text='Manage my team's expenses'").click()
        page.get_by_role("button", name="Continue").click()

        page.locator('input[name="fwork"]').fill(work_name)
        page.get_by_role("button", name="Continue").last.click()
    else:
        page.locator("text='Track and budget expenses'").click()
        page.get_by_role("button", name="Continue").click()

    page.locator('input[name="fname"]').fill(first_name)
    page.locator('input[name="lname"]').fill(last_name)
    page.get_by_role("button", name="Continue").last.click()

    return browser, page, email, work_name, context


# Add the member to the workspace using `user_email2`
def add_member(page, user_email2):
    my_settings = page.locator('button[aria-label="My settings"]')
    expect(my_settings).to_be_visible()
    my_settings.click()

    work_spaces = page.locator('div[aria-label="Workspaces"]')
    expect(work_spaces).to_be_visible()
    work_spaces.click()

    my_work = page.locator('button[aria-label="row"]')
    expect(my_work).to_be_visible()
    my_work.click()

    page.locator('div[data-tag="pressable"]', has_text="Default Currency").last.click()
    page.locator('input[aria-label="Default currency"]').last.fill("USD")
    page.locator('button[aria-label="USD - $"]').last.click()

    features = page.locator('div[aria-label="Members"]')
    expect(features).to_be_visible()
    features.click()

    invite_member = page.locator('button:has-text("Invite member")')
    expect(invite_member).to_be_visible()
    invite_member.click()

    page.locator('input[aria-label="Name, email, or phone number"]').fill(user_email2)
    page.wait_for_timeout(2000)

    # try:
    #     page.locator(f'button[aria-label="{user_email2}"]').nth(0).click()
    # except:
    page.locator('button[aria-label="Sai Yagna"]').first.click()

    page.locator('button:has-text("Next")').click()

    page.get_by_test_id("WorkspaceInviteMessagePage").get_by_role("button", name="Invite").click()

    page.wait_for_timeout(2000)

    features = page.locator('div[aria-label="More features"]').click()

    workflow = page.locator(
        'button[aria-label="Configure how spend is approved and paid."]'
    ).click()

    workflows = page.locator('div[aria-label="Workflows"]').click()

    approval = page.locator(
        'button[aria-label="Require additional approval before authorizing a payment."]'
    ).click()

    back = page.locator('button[aria-label="Back"]').nth(0).click()

    inbox = page.locator('button[aria-label="Inbox"]').click()


# Member leaves the workspace
def submit_expense(page, work_name_admin, amount, i):
    page.locator(
        'button[aria-label="Start chat (Floating action)"][tabindex="0"]'
    ).click()

    submit_expense_button = page.locator('div[aria-label="Submit expense"]').nth(0)
    expect(submit_expense_button).to_be_visible()
    submit_expense_button.click()

    manual_button = page.locator('button[aria-label="Manual"]')
    expect(manual_button).to_be_visible()
    manual_button.click()

    page.locator('button[aria-label="Select a currency"]').last.click()
    page.locator('input[aria-label="Search"]').last.fill("USD")
    page.locator('button[aria-label="USD - $"]').last.click()

    page.locator('input[role="presentation"]').first.fill(str(amount))

    next_button = page.locator('button[data-listener="Enter"]', has_text="Next").first
    expect(next_button).to_be_visible()
    next_button.click()

    page.get_by_test_id("selection-list-text-input").click()
    page.get_by_test_id("selection-list-text-input").fill(work_name_admin)

    page.wait_for_timeout(2000)
    page.get_by_test_id("selection-list").get_by_label(work_name_admin).click()

    merchant_field = page.locator('div[role="menuitem"]', has_text="Merchant")
    expect(merchant_field).to_be_visible()
    merchant_field.click()

    page.locator('input[aria-label="Merchant"]').fill("Test Merchant")

    save_button = page.locator("button", has_text="Save")
    expect(save_button).to_be_visible()
    save_button.click()

    save_button = page.locator('button[data-listener="Enter"]', has_text="Submit").last
    expect(save_button).to_be_visible()
    save_button.click()


def hold_and_see(page, fwork_name_admin):
    page.wait_for_timeout(2000)
    page.locator('button[aria-label="Navigates to a chat"]', has_text=fwork_name_admin).last.click()

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]', has_text="owes")
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()

    view_details = page.locator('button[aria-label="View details"]', has_text="$300.00")
    view_details.wait_for(state="visible", timeout=30000)
    view_details.click()

    chat_message = page.locator('div[aria-label="Cash"]', has_text="$200.00").nth(0)
    chat_message.click()

    button = page.locator('button[aria-label="$200.00 for Test Merchant"]').nth(1)
    button.click()

    hold = page.locator('button:has-text("Hold")')
    expect(hold).to_be_visible()
    hold.click()

    input_field = page.locator('input[aria-label="Reason"]')
    expect(input_field).to_be_visible()
    input_field.fill("y")

    hold_expense = page.locator('button:has-text("Hold expense")')
    expect(hold_expense).to_be_visible()
    hold_expense.click()

    got_it = page.locator('button:has-text("Got it")')
    expect(got_it).to_be_visible()
    got_it.click()

    my_settings = page.locator('button[aria-label="My settings"]')
    expect(my_settings).to_be_visible()
    my_settings.click()

    trouble = page.locator('div[aria-label="Troubleshoot"]')
    expect(trouble).to_be_visible()
    trouble.click()

    button_off = page.locator('button[aria-label="Force offline"]').click()
    inbox = page.locator('button[aria-label="Inbox"]').click()

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]').nth(1)
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()

    approve = page.locator('button:has-text("Approve")').nth(3)
    expect(approve).to_be_visible()
    approve.click()

    approve_only_100 = page.locator('button:has-text("Approve only")')
    expect(approve_only_100).to_be_visible()
    approve_only_100.click()

    workspace_chat = page.locator('button[aria-label="Navigates to a chat"]').nth(1)
    expect(workspace_chat).to_be_visible()
    workspace_chat.click()

    svg_element = workspace_chat.locator('svg[fill="#03D47C"]')
    expect(svg_element).not_to_be_visible()


def test_run(
    admin_first_name="Yagna",
    admin_last_name="Sai",
    member_first_name="Sai",
    member_last_name="Yagna",
):
    with sync_playwright() as p:
        # Log in both users and start tracing
        browser_member, page_member, user_email2, _, context_member = login(
            p, f"t56826807+{1234}@gmail.com", member_first_name, member_last_name
        )

        browser_admin, page_admin, _, fwork_name_admin, context_admin = login(
            p,
            f"t56826807+{4321}@gmail.com",
            admin_first_name,
            admin_last_name,
            "woek_12ka4",
        )

        try:
            add_member(page_admin, user_email2)
            submit_expense(page_member, fwork_name_admin, 100, 0)
            submit_expense(page_member, fwork_name_admin, 200, 1)
            page_admin.bring_to_front()
            hold_and_see(page_admin, fwork_name_admin)
        finally:
            # Ensure traces are stopped, saved, and cleaned even if the test fails
            context_admin.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            context_member.tracing.stop(path="/app/expensify/user_tool/output_browser2.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser2.zip")
            browser_admin.close()
            browser_member.close()


if __name__ == "__main__":
    test_run()
