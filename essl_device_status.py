"""
ESSL Biometric Device Monitor
- Inline screenshot in email body
- Subject: Biometric Device Status — 30 Mar 2026
- Runs every hour between 8 AM and 8 PM only
Run: python essl_device_status.py
"""

import os, smtplib, logging, schedule, time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

PORTAL_URL         = "http://35.154.100.94:99/iclock/Main.aspx"
USERNAME           = "Dashboard"
PASSWORD           = "D@$h80#$"
GMAIL_SENDER       = "charan.bijapur@rentomojo.com"
GMAIL_APP_PASSWORD = "zyit xolw btzg rjyk"
RECIPIENTS         = ["whleads@rentomojo.com",
"core.ops@rentomojo.com",
"cityleadops@rentomojo.com",
"lcleads@rentomojo.com",
"hrbp@rentomojo.com",
"admin.wh@rentomojo.com",
"it@rentomojo.com"]
SCREENSHOT_PATH    = "essl_dashboard.png"
RUN_EVERY_MINUTES  = 120
START_HOUR         = 8    # 8 AM
END_HOUR           = 20   # 8 PM

# These 2 are always excluded from online/offline count
EXCLUDED_DEVICES    = ["Bangalore Stock", "Test Device"]
TOTAL_DEVICES       = 17   # full fleet including excluded
MONITORED_DEVICES   = 15   # only these are counted as online/offline

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  SCRAPE + SCREENSHOT  (exact working logic from version 6)
# ─────────────────────────────────────────────────────────────
def scrape_and_screenshot() -> dict:
    counts = {"online": 0, "offline": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-gpu","--no-sandbox","--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            ignore_https_errors=True,
        )
        page = context.new_page()

        try:
            # Open portal
            log.info("Opening portal ...")
            page.goto(PORTAL_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Find login popup frame
            log.info("Finding login frame ...")
            login_frame = None
            for attempt in range(10):
                all_frames = page.frames
                log.info(f"Attempt {attempt+1}: {len(all_frames)} frame(s) found")
                for frame in all_frames:
                    try:
                        url = frame.url
                        log.info(f"  Frame URL: {url}")
                        pwd = frame.locator("input[type='password']").first
                        pwd.wait_for(state="visible", timeout=1000)
                        login_frame = frame
                        log.info(f"  Login frame found: {url}")
                        break
                    except Exception:
                        continue
                if login_frame:
                    break
                page.wait_for_timeout(1000)

            if not login_frame:
                log.warning("No login iframe — trying main page.")
                login_frame = page

            # Fill username
            log.info("Filling Login Name ...")
            for sel in ["input[name='LoginName']", "input[name='UserID']",
                        "input[name='username']", "input[type='text']",
                        "input:not([type='password']):not([type='submit'])"
                        ":not([type='button']):not([type='hidden'])"]:
                try:
                    el = login_frame.locator(sel).first
                    el.wait_for(state="visible", timeout=2000)
                    el.fill(USERNAME)
                    log.info(f"  Username filled: {sel}")
                    break
                except Exception:
                    continue

            # Fill password
            log.info("Filling Password ...")
            for sel in ["input[type='password']", "input[name='Password']"]:
                try:
                    el = login_frame.locator(sel).first
                    el.wait_for(state="visible", timeout=2000)
                    el.fill(PASSWORD)
                    log.info(f"  Password filled: {sel}")
                    break
                except Exception:
                    continue

            # Click login
            log.info("Clicking Login ...")
            for sel in ["input[value='Login']", "button:has-text('Login')",
                        "input[type='submit']", "button[type='submit']"]:
                try:
                    el = login_frame.locator(sel).first
                    el.wait_for(state="visible", timeout=2000)
                    el.click()
                    log.info(f"  Login clicked: {sel}")
                    break
                except Exception:
                    continue

            # Wait for dashboard
            log.info("Waiting for dashboard ...")
            page.wait_for_timeout(4000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            log.info(f"URL after login: {page.url}")

            # Find dashboard content frame
            log.info("Finding dashboard frame ...")
            content_frame = None
            for attempt in range(5):
                for frame in page.frames:
                    try:
                        log.info(f"  Checking frame: {frame.url}")
                        sel = frame.locator("select").first
                        sel.wait_for(state="visible", timeout=2000)
                        content_frame = frame
                        log.info(f"  Dashboard frame: {frame.url}")
                        break
                    except Exception:
                        continue
                if content_frame:
                    break
                page.wait_for_timeout(1000)

            if not content_frame:
                log.warning("Using main page as content frame.")
                content_frame = page

            # Read counts
            counts = _read_counts(content_frame)
            log.info(f"Counts: {counts}")

            # Set Status = All
            log.info("Setting Status = All ...")
            changed = content_frame.evaluate("""() => {
                let changed = false;
                for (let sel of document.querySelectorAll('select')) {
                    const allOpt = [...sel.options]
                        .find(o => o.text.trim().toLowerCase() === 'all');
                    if (allOpt) {
                        sel.value = allOpt.value;
                        sel.dispatchEvent(new Event('change', {bubbles:true}));
                        changed = true;
                    }
                }
                return changed;
            }""")
            log.info(f"Status=All: {changed}")
            page.wait_for_timeout(1000)

            # Click Refresh
            log.info("Clicking Refresh ...")
            content_frame.evaluate("""() => {
                const all = [
                    ...document.querySelectorAll('input[type=submit]'),
                    ...document.querySelectorAll('input[type=button]'),
                    ...document.querySelectorAll('button'),
                    ...document.querySelectorAll('a'),
                ];
                const btn = all.find(b =>
                    /refresh/i.test(b.value||b.innerText||b.title||''));
                if (btn) btn.click();
            }""")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                page.wait_for_timeout(3000)

            # Re-read counts after refresh
            counts = _read_counts(content_frame)
            log.info(f"Final counts: {counts}")

            # Zoom 75% + screenshot
            content_frame.evaluate("document.body.style.zoom='75%'")
            page.wait_for_timeout(500)
            page.screenshot(path=SCREENSHOT_PATH, full_page=False)
            log.info(f"Screenshot saved → {SCREENSHOT_PATH}")

        except PWTimeout as e:
            log.error(f"Timeout: {e}")
            try: page.screenshot(path=SCREENSHOT_PATH)
            except: pass
        except Exception as e:
            log.error(f"Error: {e}")
            try: page.screenshot(path=SCREENSHOT_PATH)
            except: pass
        finally:
            context.close()
            browser.close()
            log.info("Browser closed.")

    return counts


def _read_counts(frame) -> dict:
    try:
        return frame.evaluate("""() => {
            let online = 0, offline = 0;
            const body = document.body.innerText || '';
            const onM  = body.match(/(\\d+)\\s*\\n?\\s*Online Devices/i);
            const offM = body.match(/(\\d+)\\s*\\n?\\s*Offline Devices/i);
            if (onM)  online  = parseInt(onM[1]);
            if (offM) offline = parseInt(offM[1]);
            if (online === 0 && offline === 0) {
                for (let el of document.querySelectorAll('div,td,span')) {
                    const t = (el.innerText||'').trim();
                    if (/online devices/i.test(t) && el.children.length <= 3) {
                        const m = t.match(/^(\\d+)/); if(m) online=parseInt(m[1]);
                    }
                    if (/offline devices/i.test(t) && el.children.length <= 3) {
                        const m = t.match(/^(\\d+)/); if(m) offline=parseInt(m[1]);
                    }
                }
            }
            return { online, offline };
        }""")
    except Exception as e:
        log.warning(f"Count read error: {e}")
        return {"online": 0, "offline": 0}


# ─────────────────────────────────────────────────────────────
#  SEND EMAIL — inline screenshot in body
# ─────────────────────────────────────────────────────────────
def send_email(online: int, offline: int):
    today = datetime.now().strftime("%d %b %Y")   # date only, no time

    # Portal returns counts including excluded devices sometimes.
    # Cap online+offline to MONITORED_DEVICES (15) max to be safe.
    offline = min(offline, MONITORED_DEVICES)
    online  = MONITORED_DEVICES - offline          # always sums to 15

    # ── Subject ───────────────────────────────────────────────
    subject = f"Biometric Device Status — {today}"

    # ── Offline alert block ───────────────────────────────────
    if offline > 0:
        alert_html = f"""
        <div style="background:#fef2f2;border-left:5px solid #ef4444;
                    padding:14px 18px;margin:16px 0;border-radius:4px;">
          <p style="margin:0;font-size:14px;font-weight:700;color:#dc2626;">
            &#9888; Alert — {offline} Device(s) Offline
          </p>
          <p style="margin:6px 0 0;font-size:13px;color:#7f1d1d;">
            Please check the highlighted device(s) immediately.
          </p>
        </div>"""
        status_line = (
            f"<strong style='color:#dc2626;'>{offline} device(s) are currently "
            f"Offline</strong> and require immediate attention. "
            f"{online} out of {TOTAL_DEVICES} devices are Online."
        )
    else:
        alert_html  = ""
        status_line = (
            f"All <strong style='color:#16a34a;'>{online} devices "
            f"are Online</strong> and working fine."
        )

    # ── HTML body ─────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif;">
<div style="max-width:780px;margin:24px auto;background:#fff;
            border-radius:10px;overflow:hidden;
            box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:#1e3a5f;padding:22px 28px;">
    <h1 style="margin:0;color:#fff;font-size:18px;">
      &#128204; Biometric Device Status
    </h1>
    <p style="margin:5px 0 0;color:#93c5fd;font-size:13px;">{today}</p>
  </div>

  <!-- Body -->
  <div style="padding:24px 28px;">

    <p style="font-size:15px;color:#1e293b;margin:0 0 6px;">Hi Team,</p>

    <p style="font-size:14px;color:#475569;margin:0 0 8px;line-height:1.8;">
      Please find the status of the biometric devices as on <strong>{today}</strong>.
    </p>

    <p style="font-size:14px;color:#475569;margin:0 0 20px;line-height:1.8;">
      If any Warehouse Biometric devices are offline, kindly reconnect them to Wi-Fi.
      For troubleshooting assistance, please coordinate with the IT team at
      <a href="mailto:it@rentomojo.com" style="color:#1e3a5f;font-weight:600;">
        it@rentomojo.com
      </a>.
    </p>

    <!-- Inline screenshot -->
    <p style="font-size:14px;font-weight:600;color:#1e3a5f;margin:0 0 10px;">
      &#128247; Live Dashboard Screenshot:
    </p>
    <img src="cid:dashboard_screenshot"
         style="width:100%;border-radius:6px;
                border:1px solid #e2e8f0;display:block;" />

    <p style="font-size:12px;color:#94a3b8;margin:16px 0 0;text-align:center;">
      Automated report — runs every {RUN_EVERY_MINUTES} hour between
      {START_HOUR}:00 AM – {END_HOUR - 12}:00 PM &nbsp;|&nbsp; ESSL eTimeTrackLite
    </p>
  </div>

</div>
</body>
</html>"""

    # ── Build MIME — inline image via Content-ID ──────────────
    msg = MIMEMultipart("related")
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = ", ".join(RECIPIENTS)
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)

    # Embed screenshot inline (appears in email body, not as attachment)
    if os.path.exists(SCREENSHOT_PATH):
        with open(SCREENSHOT_PATH, "rb") as f:
            img = MIMEImage(f.read(), "png")
            img.add_header("Content-ID", "<dashboard_screenshot>")
            img.add_header("Content-Disposition", "inline",
                           filename="dashboard.png")
            msg.attach(img)
        log.info("Screenshot embedded inline in email body.")
    else:
        log.warning("Screenshot not found.")

    log.info(f"Sending to: {', '.join(RECIPIENTS)}")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER, RECIPIENTS, msg.as_string())
        log.info("✅ Email sent!")
    except smtplib.SMTPAuthenticationError:
        log.error("❌ Gmail auth failed.")
    except Exception as e:
        log.error(f"❌ Email error: {e}")


# ─────────────────────────────────────────────────────────────
#  JOB — only runs between 8 AM and 8 PM
# ─────────────────────────────────────────────────────────────
def job():
    now_hour = datetime.now().hour
    if not (START_HOUR <= now_hour < END_HOUR):
        log.info(f"Outside active hours ({START_HOUR}:00–{END_HOUR}:00). Skipping.")
        return

    log.info("=" * 50)
    log.info(f"  Run — {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    log.info("=" * 50)
    counts = scrape_and_screenshot()
    log.info(f"Online: {counts['online']}  Offline: {counts['offline']}")
    send_email(counts["online"], counts["offline"])


# ─────────────────────────────────────────────────────────────
#  SCHEDULER
# ─────────────────────────────────────────────────────────────
def main():
    log.info("=" * 50)
    log.info("  ESSL Monitor — Started")
    log.info(f"  Active hours : {START_HOUR}:00 AM – {END_HOUR - 12}:00 PM")
    log.info(f"  Interval     : every {RUN_EVERY_MINUTES} minute(s)")
    log.info("=" * 50)

    job()  # Run immediately on start (if within hours)

    schedule.every(RUN_EVERY_MINUTES).minutes.do(job)
    log.info("Scheduler active. Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
