# Google Sheets store — setup (~10 min, free)

The bot writes reservations to a Google Sheet via a **service account** (a robot
Google identity). You do the Google Console clicks once; then drop the key file in and
run the verify script.

## 1. Create the spreadsheet
1. Make a new Google Sheet (sheets.new). Name it e.g. `California Burrito Bookings`.
2. Copy its **ID** from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_LONG_ID`**`/edit`
3. Leave the tab empty — the app writes the header row itself.

## 2. Create a Google Cloud project + service account
1. Go to https://console.cloud.google.com → create a project (any name).
2. **APIs & Services → Library** → enable both:
   - **Google Sheets API**
   - **Google Drive API**  (gspread needs it to open by key)
3. **APIs & Services → Credentials → Create credentials → Service account.**
   - Name it e.g. `voice-agent`. Skip roles/grants (not needed). Create → Done.
4. Get the key file:
   - Go to https://console.cloud.google.com/iam-admin/serviceaccounts
     (check the correct project is picked in the top bar).
   - In the table, **click the service account's email** (the row you just made).
   - On its page, click the **KEYS** tab → **ADD KEY → Create new key → JSON → Create**.
   - A `.json` file downloads. This is your credential — **keep it secret** (it's in
     `.gitignore`).

## 3. Share the sheet with the service account
1. Open the JSON key, copy the `client_email`
   (looks like `voice-agent@yourproject.iam.gserviceaccount.com`).
2. In the Google Sheet → **Share** → paste that email → give **Editor** → send.
   *(This is the step everyone forgets. No share = 403 permission error.)*

## 4. Point the app at it
Put the JSON in the repo root as `service-account.json` (git-ignored), then:

```bash
# Windows PowerShell
$env:SHEET_ID="THE_LONG_ID"
$env:GOOGLE_SERVICE_ACCOUNT_JSON="./service-account.json"

# bash
export SHEET_ID=THE_LONG_ID
export GOOGLE_SERVICE_ACCOUNT_JSON=./service-account.json
```

# Windows PowerShell
$env:SHEET_ID="1haXZsWVquBPCjGAASgh4ZY4TWBGwYVet5ssErMNVPT8"
$env:GOOGLE_SERVICE_ACCOUNT_JSON="./service-account.json"

# bash
export SHEET_ID=1haXZsWVquBPCjGAASgh4ZY4TWBGwYVet5ssErMNVPT8
export GOOGLE_SERVICE_ACCOUNT_JSON=./service-account.json

## 5. Verify
```bash
.venv/Scripts/python scripts/verify_sheets.py
```
Expect: connects → writes a `SHEETS TEST` row → reads it back. Delete that test row
after. Errors print a targeted hint (403 = not shared, 404 = wrong ID, API disabled).

## 6. Go live
Run the tool service against Sheets by setting `STORE=sheets` (plus the two env vars
above). Everything else — book/list/transfer, the harness, the tests — is unchanged;
only the backend swaps.

## Cost & limits
Free. Limits are 300 reads + 300 writes/min/project (no daily cap) — a few
reservations/day is negligible. Idempotent booking IDs mean a retried call never
writes a duplicate row.
