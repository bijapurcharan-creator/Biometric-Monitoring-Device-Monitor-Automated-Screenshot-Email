"""
eTimeTrackLite Device Monitor - Automated Screenshot & Email
Logs in, takes screenshot of dashboard, emails it every 3 hrs (9am-8pm).
"""

import time
import smtplib
import logging
import schedule
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ─────────────────────────────────────────────
CONFIG = {
    "app_url":  "http://35.154.100.94:99/iclock/Default.aspx",
    "username": "Dashboard",
    "password": r"D@$h80#$",

    "email": {
        "smtp_host":    "smtp.gmail.com",
        "smtp_port":    587,
        "sender":       "charan.bijapur@rentomojo.com",
        "app_password": "zyit xolw btzg rjyk",
        "recipients":   ["it@rentomojo.com", "yogesh.patel@rentomojo.com,charan.bijapur@rentomojo.com"],
        "subject":      "eTimeTrackLite - Device Status Report {timestamp}",
    },

    "screenshot_dir": "screenshots",
    "page_timeout":   40,
}
# ─────────────────────────────────────────────


# ── Logging ───────────────────────────────────────────────────────────────────
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "etime_monitor.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Driver ────────────────────────────────────────────────────────────────────
def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--window-position=-32000,-32000")
    opts.add_argument("--window-size=1600,950")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--start-minimized")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(CONFIG["page_timeout"])
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


# ── LOGIN + SCREENSHOT ────────────────────────────────────────────────────────
def login_and_screenshot(driver) -> Path:
    ss_dir = Path(__file__).parent / CONFIG["screenshot_dir"]
    ss_dir.mkdir(exist_ok=True)

    log.info("Opening login page...")
    driver.get(CONFIG["app_url"])
    time.sleep(6)

    # Login
    driver.find_element(By.NAME, "StaffloginDialog$txt_LoginName").send_keys(CONFIG["username"])
    driver.find_element(By.NAME, "StaffloginDialog$Txt_Password").send_keys(CONFIG["password"])
    driver.find_element(By.NAME, "StaffloginDialog$Btn_Ok").click()
    log.info("Login submitted")

    # Wait for dashboard to fully load
    time.sleep(10)
    log.info("URL after login: %s", driver.current_url)

    if "Main.aspx" not in driver.current_url:
        raise Exception(f"Login failed — URL: {driver.current_url}")

    log.info("✅ Login successful — dashboard loaded")

    # Expand window to capture full dashboard
    driver.set_window_size(1600, 950)
    driver.set_window_position(-32000, -32000)
    time.sleep(2)

    # Take screenshot RIGHT HERE — this is the dashboard page
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = ss_dir / f"device_status_{ts}.png"
    driver.save_screenshot(str(path))
    log.info("✅ Screenshot saved: %s  (%d bytes)", path, path.stat().st_size)
    return path


# ── EMAIL ─────────────────────────────────────────────────────────────────────
def send_email(screenshot_path: Path) -> None:
    cfg = CONFIG["email"]
    now = datetime.now().strftime("%d-%b-%Y %H:%M")

    msg            = MIMEMultipart("related")
    msg["From"]    = cfg["sender"]
    msg["To"]      = ", ".join(cfg["recipients"])
    msg["Subject"] = cfg["subject"].format(timestamp=now)

    html_body = f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;">
      <h2 style="color:#1a5276;">eTimeTrackLite - Device Status Report</h2>
      <p><strong>Captured at:</strong> {now}</p>
      <p>
        Devices showing <span style="color:green;font-weight:bold;">online</span> are reachable;
        <span style="color:red;font-weight:bold;">offline</span> devices need attention.
      </p>
      <br>
      <img src="cid:screenshot" style="border:1px solid #ccc;max-width:100%;">
      <br><br>
      <p style="font-size:11px;color:#888;">
        Automated report — every 3 hours (09:00–20:00). Do not reply.
      </p>
    </body></html>
    """
    msg.attach(MIMEText(html_body, "html"))

    with open(screenshot_path, "rb") as f:
        img = MIMEImage(f.read())
    img.add_header("Content-ID", "<screenshot>")
    img.add_header("Content-Disposition", "inline", filename=screenshot_path.name)
    msg.attach(img)

    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.ehlo()
        server.starttls()
        server.login(cfg["sender"], cfg["app_password"])
        server.sendmail(cfg["sender"], cfg["recipients"], msg.as_string())

    log.info("✅ Email sent to: %s", cfg["recipients"])


# ── MAIN RUN ──────────────────────────────────────────────────────────────────
def run() -> None:
    log.info("=" * 60)
    log.info("Run started: %s", datetime.now().strftime("%d-%b-%Y %H:%M:%S"))
    driver = None
    try:
        driver = build_driver()
        screenshot_path = login_and_screenshot(driver)
        send_email(screenshot_path)
        log.info("✅ Run completed successfully")
    except Exception as exc:
        log.error("❌ Run FAILED: %s", exc, exc_info=True)
    finally:
        if driver:
            driver.quit()
            log.info("Browser closed")


# ── SCHEDULER ─────────────────────────────────────────────────────────────────
def scheduled_run():
    now = datetime.now()
    if 9 <= now.hour < 20:
        log.info("Scheduled trigger at %s", now.strftime("%H:%M"))
        run()
    else:
        log.info("Outside active hours (%s) — skipping", now.strftime("%H:%M"))


if __name__ == "__main__":
    run()  # Run immediately

    schedule.every(3).hours.do(scheduled_run)
    log.info("Scheduler active — every 3 hours between 09:00 and 20:00")
    while True:
        schedule.run_pending()
        time.sleep(60)
