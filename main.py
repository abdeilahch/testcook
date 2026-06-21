import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import time
import traceback
import json
from playwright.sync_api import sync_playwright

URLS = [
    "https://costream.mycloud.intranatixis.com",
    "https://cockpit.intranatixis.com",
    "https://mycloud.d.bbg/auth/saml/login"
]


def append_text(text):
    txt.insert(tk.END, text + "\n")
    txt.see(tk.END)
    root.update_idletasks()


def collect_data(page, context):

    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass

    try:
        horizon = page.query_selector("#Kerberos_Horizon")
        if horizon:
            horizon.click()
            page.wait_for_timeout(3000)
    except:
        pass

    stable = 0
    previous_count = -1

    for _ in range(30):

        cookies = context.cookies()
        current_count = len(cookies)

        if current_count > 0 and current_count == previous_count:
            stable += 1
        else:
            stable = 0

        previous_count = current_count

        if stable >= 3:
            break

        time.sleep(1)

    cookies = context.cookies()

    try:
        local_storage = page.evaluate("""
        () => {
            const data = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                data[key] = localStorage.getItem(key);
            }
            return data;
        }
        """)
    except:
        local_storage = {}

    return cookies, local_storage


def run():

    def worker():

        txt.delete("1.0", tk.END)

        try:

            with sync_playwright() as p:

                browser = p.chromium.launch(headless=True)

                context = browser.new_context()

                results = {}

                for url in URLS:

                    page = context.new_page()

                    append_text(f"Ouverture : {url}")

                    page.goto(url)

                    cookies, local_storage = collect_data(page, context)

                    results[url] = {
                        "cookies": cookies,
                        "localStorage": local_storage
                    }

                    time.sleep(2)

                txt.delete("1.0", tk.END)

                for url, data in results.items():

                    append_text("=" * 100)
                    append_text(url)
                    append_text("=" * 100)

                    append_text("")
                    append_text("COOKIES JSON")
                    append_text("")

                    append_text(
                        json.dumps(
                            data["cookies"],
                            indent=2,
                            ensure_ascii=False
                        )
                    )

                    append_text("")
                    append_text("LOCAL STORAGE JSON")
                    append_text("")

                    append_text(
                        json.dumps(
                            data["localStorage"],
                            indent=2,
                            ensure_ascii=False
                        )
                    )

                    append_text("")
                    append_text("")

                browser.close()

        except Exception:

            txt.delete("1.0", tk.END)

            append_text("ERREUR")
            append_text("")
            append_text(traceback.format_exc())

    threading.Thread(target=worker, daemon=True).start()


root = tk.Tk()
root.title("COOKIE / LOCALSTORAGE")
root.geometry("1200x800")

btn = tk.Button(root, text="START", command=run)
btn.pack(fill="x")

txt = ScrolledText(root, wrap="none")
txt.pack(fill="both", expand=True)

root.mainloop()
