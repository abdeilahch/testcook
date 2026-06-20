import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import time
from playwright.sync_api import sync_playwright


URLS = [
    "https://www.google.com",
    "https://www.linkedin.com",
    "https://www.youtube.com"
]


def run_browser():

    def worker():

        txt.delete("1.0", tk.END)
        txt.insert(tk.END, "Démarrage Chromium embarqué...\n\n")

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False  # IMPORTANT pour SSO stable
            )

            context = browser.new_context()

            page = context.new_page()

            all_cookies = {}

            for url in URLS:

                txt.insert(tk.END, f"\n➡️ Ouverture : {url}\n")

                page.goto(url, wait_until="domcontentloaded")

                # laisser les redirections SSO / JS charger
                page.wait_for_timeout(15000)

                # attendre fin réseau (SSO)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except:
                    pass

                cookies = context.cookies()

                all_cookies[url] = cookies

                txt.insert(tk.END, f"Cookies récupérés : {len(cookies)}\n")

            # AFFICHAGE FINAL
            txt.insert(tk.END, "\n\n=====================\n")
            txt.insert(tk.END, "      COOKIES\n")
            txt.insert(tk.END, "=====================\n\n")

            for url, cookies in all_cookies.items():

                txt.insert(tk.END, f"\n🌐 {url}\n")

                for c in cookies:

                    txt.insert(tk.END, f"- {c['name']} = {c['value']}\n")
                    txt.insert(tk.END, f"  domaine : {c['domain']}\n")

            browser.close()

    threading.Thread(target=worker, daemon=True).start()


# ---------------- GUI ----------------

root = tk.Tk()
root.title("SSO Cookie Extractor (Playwright)")
root.geometry("900x600")

btn = tk.Button(root, text="Lancer extraction cookies", command=run_browser)
btn.pack(pady=10)

txt = ScrolledText(root)
txt.pack(fill="both", expand=True)

root.mainloop()
