# Setup Guide — eSSL Biometric Device Monitor

> Non-technical step-by-step guide for setting up the monitor on a Windows machine.

---

## What This Does

Automatically logs into the eSSL eTimeTrackLite dashboard every **2 hours**,
takes a screenshot of all device statuses, and emails it to the configured teams.

---

## STEP 1 — Install Python

1. Download Python 3.9+ from: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Run the installer
3. ✅ **Check "Add Python to PATH"** during install (important!)
4. Verify installation — open Command Prompt and run:
   ```
   python --version
   ```
   You should see something like `Python 3.11.x`

---

## STEP 2 — Install Google Chrome

Download and install from: [https://www.google.com/chrome/](https://www.google.com/chrome/)

---

## STEP 3 — Download the Project

```bash
git clone https://github.com/rentomojo-it/essl-biometric-monitor.git
cd essl-biometric-monitor
```

Or download the ZIP from GitHub and extract it.

---

## STEP 4 — Install Python Libraries

Open Command Prompt in the project folder and run:

```bash
pip install -r requirements.txt
playwright install chromium
```

> `playwright install chromium` downloads the browser automatically — no manual ChromeDriver needed.

---

## STEP 5 — Create Gmail App Password

> ⚠️ You **cannot** use your normal Gmail password. You need a special App Password.

1. Go to: [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already done)
3. Go to: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
4. Select App: **Mail** | Device: **Windows Computer** → Click **Generate**
5. Copy the 16-character password shown (e.g., `abcd efgh ijkl mnop`)
6. Paste it into `GMAIL_APP_PASSWORD` in the script

---

## STEP 6 — Configure the Script

Open `essl_device_status.py` in Notepad (or any text editor) and update these values near the top:

```python
PORTAL_URL         = "http://35.154.100.94:99/iclock/Main.aspx"  # eSSL server address
USERNAME           = "Dashboard"                                   # eSSL username
PASSWORD           = "your-password"                              # eSSL password

GMAIL_SENDER       = "sender@gmail.com"                           # Gmail address sending reports
GMAIL_APP_PASSWORD = "abcd efgh ijkl mnop"                        # App Password from Step 5
RECIPIENTS         = ["it@rentomojo.com", "manager@rentomojo.com"] # Who receives emails

RUN_EVERY_MINUTES  = 120   # 120 = every 2 hours. Change to 60 for every hour, etc.
START_HOUR         = 8     # Start sending at 8:00 AM
END_HOUR           = 20    # Stop sending at 8:00 PM
```

---

## STEP 7 — Test the Script

Run once manually to verify everything works:

```bash
python essl_device_status.py
```

Check your email. If it arrives correctly, proceed to Step 8.
If not, check the console output for error messages.

---

## STEP 8 — Run Continuously in Background

### Option A — Run without a console window (simplest)

```bash
pythonw essl_device_status.py
```

### Option B — Windows Task Scheduler (recommended — runs even when not logged in)

1. Open **Task Scheduler** → **Create Basic Task**
2. Name: `eSSL Biometric Monitor`
3. Trigger: **Daily** → check **Repeat task every 2 hours**
4. Action: **Start a Program**
   - Program: `python`
   - Arguments: `C:\path\to\essl_device_status.py`
   - Start In: `C:\path\to\project\`
5. Check: **Run whether user is logged on or not**
6. Click **Finish**

### Option C — NSSM Windows Service (production/server)

```bash
nssm install ESSLMonitor "C:\Python311\python.exe" "C:\path\to\essl_device_status.py"
nssm start ESSLMonitor
```

Download NSSM from: [https://nssm.cc](https://nssm.cc)

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Login fails | Open the PORTAL_URL in Chrome manually to confirm it works |
| Gmail auth error | Re-generate App Password; confirm 2FA is enabled |
| Screenshot is blank | Increase `wait_for_timeout` values in the script |
| Playwright not found | Run `playwright install chromium` again |
| Email not received | Check spam folder; verify RECIPIENTS list |

---

## Log File

All activity is logged to the console and to `logs/` in the project folder.

---

## Sample Email

- **Subject:** `Biometric Device Status — 27 May 2026`
- **Body:** Dashboard screenshot embedded inline + online/offline device count
- **Alert:** Red banner if any devices are offline
