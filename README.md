# Library Management System

A simple library system for the counter: register members and books, issue and return books by scanning QR codes or barcodes, calculate late and damage fines, print receipts, and run reports.

**Stack:** FastAPI (Python) · Vue 3 · PostgreSQL · Docker

---

## 1. Install on a Windows PC (first time)

1. Install **Docker Desktop** from <https://www.docker.com/products/docker-desktop/> and restart the PC.
   In Docker Desktop settings, turn on **"Start Docker Desktop when you sign in"** so the library system starts by itself every morning.
2. Copy this `library-system` folder to the PC, for example to `C:\library-system`.
3. Open the folder, copy `.env.example` to `.env`, open `.env` in Notepad and change:
   - `ADMIN_PASSWORD` – the first administrator password
   - `SECRET_KEY` – any long random text (40+ letters and numbers)
   - `DB_PASSWORD` – a database password
4. Double-click **`scripts\start.bat`**. The first start downloads and builds everything (5–15 minutes).
5. Open **<http://localhost:8080>** in Chrome or Edge and sign in with `admin` and your password.
6. Go to **Settings** and enter the library name, address and phone (printed on receipts and cards). Add a staff account for each person at the counter.
7. Go to **Holidays** and mark Sundays, Poya days and other closed days for the year.

After this, the system starts automatically with Docker Desktop. Use `stop.bat` / `start.bat` only if needed.

### Using it from other PCs in the library
Find the main PC's IP address (`ipconfig`, e.g. `192.168.1.20`) and open `http://192.168.1.20:8080` on the other PCs. Allow port 8080 in Windows Firewall if it does not open.

> Camera scanning works on the main PC (`localhost`). Browsers only allow the camera on other PCs over HTTPS, so use USB scanners there.

---

## 2. Barcode / QR scanners

- Use any **USB or Bluetooth scanner in keyboard (HID) mode** – no drivers or software needed.
- Buy a **2D scanner** so it reads both QR codes and normal barcodes.
- The scanner should send **Enter** after each scan (default on almost all scanners).
- Click in the big blue scan box, then scan. The system knows by itself whether you scanned a member card, a book label, or an ISBN barcode on the back of a book.
- No scanner? Click the camera button next to the scan box to use a webcam.

### Printing labels and cards
- **Book labels:** Books → tick books → *Print labels* (64 × 34 mm labels, QR + barcode + Acc. No.). Or open a book → *Print label*.
- **Member cards:** open a member → *Print card* (ID-card size, 85.6 × 54 mm, with QR code).
- **Receipts:** printed automatically after a payment; laid out for 80 mm receipt printers but also work on A4.

If your books already have barcode stickers, type that number as the book's **Acc. No.** and the existing sticker will work.

---

## 3. Daily work

| Task | Where |
|---|---|
| Member takes books | **Issue book** → scan member card → scan each book → *Issue* |
| Member returns a book | **Return book** → scan book → tick *damaged* if needed → *Confirm return* (receipt prints if a fine was paid) |
| Find a book / where it is / when it comes back | **Search** |
| New member | Home → *New member* |
| New book (or more copies) | Home → *New book* → *Save and add another copy* |
| Renew a membership | Members → open member → *Renew membership* |
| Collect an old fine | Members → open member → *Unpaid fines* → *Collect* |

---

## 4. Rules (change in Settings)

| Rule | Default |
|---|---|
| Loan period | 14 days (if the due date is a holiday it moves to the next open day) |
| Late fine | First **2 days free**, then **Rs. 2 per day**. Holidays are not counted. Option: charge the free days too once a book is more than 2 days late. |
| Damaged book | **2 × book price** |
| Max books at once | Child 2, Student 2, Life Time 3 |
| Membership period | 1 year (Life Time never expires) |
| Not for lending | Reference section |

**Example:** due 1 May, returned 8 May, 4 May is a holiday → 6 working days late → 6 − 2 free = 4 days × Rs. 2 = **Rs. 8**.

Membership types (Child, Student, Life Time) and sections (Lending, Children, Buddhist, Reference) are listed in `frontend/src/constants.js` if you need to add more.

---

## 5. Reports

Reports menu: overdue books, pending returns (by section), members not returning books, children by age (e.g. 10–11), non-active members (marked inactive or not borrowing for N months), unpaid fines, memberships expiring or expired, books by section, members by type, and payments collected. Every report can be **printed** or **exported to Excel (CSV)**.

---

## 6. Backups (important!)

- Double-click **`scripts\backup.bat`** at the end of every day. It saves a file in the `backups` folder.
- Copy backup files to a USB drive or cloud storage every week.
- To restore: drag a backup `.sql` file onto **`scripts\restore.bat`** (this replaces all current data).
- Linux/macOS: `scripts/backup.sh` (can be run daily with cron).

Tip: use Windows **Task Scheduler** to run `backup.bat` every evening automatically.

---

## 7. For developers

```
library-system/
├── docker-compose.yml        PostgreSQL + backend + frontend (nginx)
├── backend/                  FastAPI app
│   └── app/
│       ├── main.py           app setup, creates tables + first admin
│       ├── models.py         Member, Book, Loan, Payment, Holiday, User, AppSetting
│       ├── schemas.py        request/response models
│       ├── services.py       fines, due dates, numbering, settings
│       └── routers/          auth, members, books, circulation, search,
│                             reports, payments, holidays, settings, codes
├── frontend/                 Vue 3 + Vite, served by nginx (proxies /api)
│   └── src/views/            one file per screen
└── scripts/                  start / stop / backup / restore
```

Run without Docker:

```bash
# backend (needs PostgreSQL, or use SQLite for testing)
cd backend
pip install -r requirements.txt
DATABASE_URL=sqlite:///./dev.db uvicorn app.main:app --reload

# frontend (another terminal) – opens on http://localhost:5173
cd frontend
npm install
npm run dev
```

API documentation: <http://localhost:8000/docs> when running the backend directly.

Tables are created automatically on first start. For future database changes in production, add Alembic migrations.

After changing code with Docker: run `docker compose up -d --build`.
