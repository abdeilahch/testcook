import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import traceback
import time
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


def wait_ready(page, context, url):

    log(f"OPEN {url}")

    page.goto(url)

    cookies_ok = False
    stable_count = 0

    # boucle de verification (max ~30s)
    for _ in range(60):

        try:
            cookies = context.cookies()

            # condition : cookies présents
            if len(cookies) > 0:
                stable_count += 1
            else:
                stable_count = 0

            # condition : pas de navigation active
            state = page.evaluate("document.readyState")

            if state == "complete" and stable_count >= 3:
                cookies_ok = True
                break

            time.sleep(0.5)

        except:
            pass

    return context.cookies(), cookies_ok


def run():

    def worker():
        try:
            log("START\n")

            with sync_playwright() as p:

                browser = p.chromium.launch(
                    headless=False
                )

                context = browser.new_context()

                results = {}

                for url in URLS:

                    page = context.new_page()

                    cookies, ok = wait_ready(page, context, url)

                    log(f"\nDONE {url} | stable={ok}")

                    results[url] = cookies

                    time.sleep(2)  # interval entre sites

                log("\n====================")
                log("COOKIES RESULT")
                log("====================\n")

                for url, cookies in results.items():

                    log(f"\n--- {url} ---")

                    for c in cookies:
                        log(f"{c['name']} = {c['value']}")

            log("\nEND")

        except Exception:
            log("FATAL ERROR")
            log(traceback.format_exc())

    threading.Thread(target=worker, daemon=True).start()


# GUI
root = tk.Tk()
root.title("COOKIE MONITOR")
root.geometry("900x600")

btn = tk.Button(root, text="START", command=run)
btn.pack(pady=10)

txt = ScrolledText(root)
txt.pack(fill="both", expand=True)

root.mainloop()
