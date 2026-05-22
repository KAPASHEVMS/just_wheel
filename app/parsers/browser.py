"""Singleton WebDriver для Selenium — синхронный, без asyncio."""
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        opts = Options()
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

        # Ищем Chromium от Playwright
        userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        base = os.path.join(userprofile, "AppData", "Local", "ms-playwright")
        found = False
        for ver_dir in sorted(os.listdir(base) if os.path.isdir(base) else [], reverse=True):
            chrome_exe = os.path.join(base, ver_dir, "chrome-win64", "chrome.exe")
            if os.path.exists(chrome_exe):
                opts.binary_location = chrome_exe
                # Извлекаем версию из имени папки: chromium-1217
                # Playwright: chromium-XXXX, actual version in chrome.exe
                found = True
                break

        if not found:
            raise RuntimeError("Chromium not found. Install: playwright install chromium")

        # ChromeDriver — используем совместимую версию (147)
        # webdriver_manager автоматически подбирает драйвер под версию Chrome
        try:
            service = Service(ChromeDriverManager(driver_version="147.0.7727.15").install())
        except Exception:
            # Если конкретная версия недоступна, пробуем последнюю
            service = Service(ChromeDriverManager().install())

        _driver = webdriver.Chrome(service=service, options=opts)
        _driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.quit()
        _driver = None
