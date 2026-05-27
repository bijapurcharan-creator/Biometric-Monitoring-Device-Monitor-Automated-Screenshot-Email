# Changelog

All notable changes to the eSSL Biometric Monitor are documented here.

---

## [2.0.0] — May 2026 — Current

### Migrated to Playwright
- Replaced Selenium + webdriver-manager with **Playwright (Chromium)**
- Playwright auto-manages browser binary — no manual ChromeDriver download needed
- More reliable iframe detection and frame navigation

### New Features
- **Device count parsing** — reads Online/Offline count live from dashboard
- **Dynamic offline alert block** in email — red banner when devices are offline
- **Wider recipient list** — now sends to WH Leads, Core Ops, City Lead Ops, LC Leads, HRBP, Admin WH
- **Excluded devices list** — `EXCLUDED_DEVICES` config to skip test/staging devices from count
- **Email subject** changed to date-only: `Biometric Device Status — 27 May 2026`
- **SMTP_SSL on port 465** instead of STARTTLS 587

### Improvements
- JavaScript-based dropdown selection (works across all `<select>` elements)
- Screenshot zoom reduced to 75% for full-page capture
- Scroll-down step removed (zoom handles full visibility)
- Cleaner HTML email template with RentoMojo navy header

---

## [1.1.0] — April 2026

### Fixes & Improvements (Selenium version)
- Added **75% browser zoom** via `document.body.style.zoom` to capture full dashboard
- Added **Device Status dropdown → "All"** selection before screenshot (6 locator fallbacks)
- Added **scroll down 200px** as extra safety for cut-off rows
- Fixed window positioning (`-32000,-32000`) to keep Chrome off-screen

---

## [1.0.0] — March 2026 — Initial Release

### Selenium-based implementation
- Chrome browser automation via Selenium WebDriver
- Auto-managed ChromeDriver via `webdriver-manager`
- Login to eTimeTrackLite portal and screenshot dashboard
- HTML email with embedded screenshot via Gmail SMTP (STARTTLS 587)
- Scheduler runs every 3 hours between 09:00–20:00 IST
- Logs written to `logs/etime_monitor.log`
- Anti-detection: custom user-agent, CDP `navigator.webdriver = undefined`
