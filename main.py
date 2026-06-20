import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import traceback
from playwright.sync_api import sync_playwright


URLS = [
    "https://www.google.com",
    "https://www.linkedin.com",
    "https://www.youtube.com"
]


def log(msg):
    txt.insert(tk.END, msg + "\n")
    txt.see(tk.END)
    root.update()


def run():

    def worker():
        try:
            log("START")

            with sync_playwright() as p:

                log("Launch Chromium")

                browser = p.chromium.launch(headless=False)
                context = browser.new_context()

                for url in URLS:

                    try:
                        log(f"\nOPEN: {url}")

                        page = context.new_page()
                        page.goto(url)

                        log("WAIT 15s")
                        page.wait_for_timeout(15000)

                        cookies = context.cookies()

                        log(f"COOKIES: {len(cookies)}")

                        for c in cookies:
                            log(f"{c['name']} = {c['value']}")

                    except Exception:
                        log("PAGE ERROR")
                        log(traceback.format_exc())

                browser.close()
                log("END")

        except Exception:
            log("FATAL ERROR")
            log(traceback.format_exc())

    threading.Thread(target=worker, daemon=True).start()


# GUI
root = tk.Tk()
root.title("DEBUG COOKIE TOOL")
root.geometry("900x600")

btn = tk.Button(root, text="START", command=run)
btn.pack()

txt = ScrolledText(root)
txt.pack(fill="both", expand=True)

root.mainloop()
