import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import traceback
from playwright.sync_api import sync_playwright


URLS = [
    "https://costream.mycloud.intranatixis.com",
    "https://cockpit.intranatixis.com",
    "https://mycloud.d.bbg/auth/saml/login"
]


def log(msg):
    txt.insert(tk.END, msg + "\n")
    txt.see(tk.END)
    root.update()


def wait_redirect_and_cookies(page, context):

    # attendre navigation + JS
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass

    # click si horizon
    try:
        el = page.query_selector("#Kerberos_Horizon")
        if el:
            el.click()
            log("Kerberos_Horizon CLICK")
            page.wait_for_timeout(3000)
    except:
        pass

    # attendre stabilité cookies
    stable = 0
    last = -1

    for _ in range(30):

        cookies = context.cookies()
        count = len(cookies)

        if count == last and count > 0:
            stable += 1
        else:
            stable = 0

        last = count

        if stable >= 3:
            return cookies

        time.sleep(1)

    return context.cookies()


def run():

    def worker():

        try:
            log("START")

            with sync_playwright() as p:

                browser = p.chromium.launch(headless=False)
                context = browser.new_context()

                results = {}

                for i, url in enumerate(URLS):

                    log(f"\nOPEN {url}")

                    page = context.new_page()
                    page.goto(url)

                    cookies = wait_redirect_and_cookies(page, context)

                    results[url] = cookies

                    log(f"COOKIES {url}: {len(cookies)}")

                    time.sleep(2)

                log("\n===== COOKIES =====\n")

                for url, cookies in results.items():

                    log(f"\n--- {url} ---")

                    for c in cookies:
                        log(f"{c['name']} = {c['value']}")

                browser.close()

            log("END")

        except Exception:
            log("ERROR")
            log(traceback.format_exc())

    threading.Thread(target=worker, daemon=True).start()


# GUI
root = tk.Tk()
root.title("COOKIE TOOL")
root.geometry("900x600")

tk.Button(root, text="START", command=run).pack()

txt = ScrolledText(root)
txt.pack(fill="both", expand=True)

root.mainloop()
