from playwright.sync_api import sync_playwright, expect
from utils.trace_cleaner import trace_cleaner

transition_url = "https://dev.new.expensify.com:8082/transition?accountID=19140171&email=testexpensifyturing%2B033%40gmail.com&shortLivedAuthToken=4D757E8651E38852A491A3C7E3E63EA560712E5BB6642A0CD964D8AFAF1AFA50AF2D551B6951F5A8487B78F632A8311547E414F41707E88AFDDACEF2B30EE59046FF402E7B9E63ADADFC93D4C4D27515CB28225CE6DEE1160B6CC6F7BEEAB867C9CDDAFEAE6196E9DC548B26AEE836E2DA91C174A0E2F77F4C559A13CDE4B47BDFB301B0F30435A710E48ACBE56FF86D919EDCBFCB0DD99C51BA8DC111499572BFA31CA5192DAA0F47381F07DAC334389D7941D4C87528CEF3319A2638440D52C96E3F12B2D0AA0A68319944491FBE6964C026DFE995A41AD51B29A84061C0F21992A68DE0EBDEAEB6780EBEEEBD42435BE798E6AE58C2CF6BB6D5A43087E5930469DC588C7DED2DFD9DE9E266047719DE59C50FAB3DD4E1C3F274BACBB83D5CDE4E857D39532E04CE6184424041C13F0461B0400BFC9691FBB85DF7C9D5E78DE86B0A4C8EECB9D593A993850F8C2B0ACF0C20942A6F03F852B9536BFD7C6E2A&encryptedAuthToken=hbEFkv5efCeb2TDstpowyrpGEE9jEwW2S1b131FQSTQ8Ocn8XSp9R2j3PUu8jAoCGpMpuj%2FcWkKWTrb5iOjDaPI8s2mdvdD5SmDbAad6f%2F%2FZD%2FPEXKLdSbpDRr%2BLQDODGGf%2Fs1990KeF%2Fomxjez8k%2FJukKBzCkUBcHt5ApenMAT7gnPdYzLG%2BGUhUuO7ThFZB8YixKqH2RAyvwDazVZyercuy37zzJtrX6XzFWexJc%2F0WHdsrw0ltC5p1agxH5%2ByfHi4%2B0pUQcTw0e0i7rybeIqIYK85w%2Fo1q0jYdSiW8wCMlQM8nXELq8ITGmU%2F1mbNH5Y%2FSCf4KXNOFOlj5U5SeUtHwYhkig6Ly2t%2F%2FFD%2FBs%2BhMET42JzkFJxfX8dhuYIM20Su3f4Q2abMfkB9NQksOBBIN%2FJUINR7WbkxNnhe%2FzEQQBuIdgg9m%2BPgeh%2F%2FDPEytFICuOGAx%2BVOE8jeQGoKzS2p7E%2FQjSvR4WWH6r7Xsn287XtqdWl3OP9ljebP1yyp87aOPIcOJzM7ZlmAx1IZFwIUmCN8rDUg%2FcCEEAKa5it1TRwJ6YmCk3kpySAkBLU%2Bn8z%2FbwCYP2uAhwFZ21Xp0yHj2%2B%2FSzkMOenTQ2rS2jvIPPR8yMyNWlVSjyJuSsYeGdscJKdq3tdu%2B76qILJvyV7U23V46R1KtZrjtkmoLCjR1BzmaICe79gUZ%2BoQcPM4NGs6BLb9fgPLFiGweMt5av%2Fk9bqtbGgNzJU8RFghcBHQayAnvLa8xD51WUg4vVB5qpR8sPNTcWmX59UarWbjmUBWGDUf0RHlPArZUMg2WB9JrJGcmKW%2FzuSYd9jYZq4wEbfQb%2BhZh5PG9oRf%2F6zcBlfXUY0u01okhxVdJJXiJEePb160AA67VNq6xE4ebYmhLKFxo9xQO%2BtGqbxHNNh%2BIWktvdO66KMvA3kqNCr3VNoDd83NXSb1olOcuNCG0m5kmHkf4IV9ViFdV5p9nbEA4IEc%2FyEiNt500fOT4OutvS7Wexq%2BAfvjgCuNTPbZCjoRt&exitTo=concierge&shouldForceLogin=false

def test_expensify_51546():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": "http://127.0.0.1:8080/"},
            slow_mo=500
        )
        context = browser.new_context(ignore_https_errors=True)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        try:
            # Navigate to a transition URL which shows the "Session expired" page and click on sign in
            page.goto(transition_url)
            page.get_by_text("Please sign in again").click()

            # Verify session expired page is not visible anymore
            expect(page.get_by_text("Your session has expired")).not_to_be_visible()
            # Verify the page URL does not contain "transition", wait for a short time to let the URL reflect
            page.wait_for_timeout(500)
            assert "transition" not in page.url
        finally:
            trace_path = "/app/expensify/user_tool/output_browser1.zip"
            context.tracing.stop(path=trace_path)
            trace_cleaner(trace_path)
            browser.close()