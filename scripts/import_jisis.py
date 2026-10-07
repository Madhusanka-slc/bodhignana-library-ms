"""Import a J-ISIS export (userdb_flat.csv + libcat_flat.csv) into the library database.

Run inside the backend container, from the library-system folder:

    docker compose cp "<export folder>/userdb_flat.csv" backend:/tmp/export/userdb_flat.csv
    docker compose cp "<export folder>/libcat_flat.csv" backend:/tmp/export/libcat_flat.csv
    docker compose cp scripts/import_jisis.py backend:/tmp/import_jisis.py
    docker compose exec backend python /tmp/import_jisis.py /tmp/export --dry-run
    docker compose exec backend python /tmp/import_jisis.py /tmp/export

Everything is inserted in one transaction: either all records go in or none.
Records already in the database (same Membership No, or same Acc. No. and title) are skipped.
Records that need a librarian's attention are listed in <export folder>/import_report.csv.
"""
import csv
import os
import re
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.getcwd())

from sqlalchemy import String, insert, select, text  # noqa: E402

from app.database import engine  # noqa: E402
from app.models import AVAILABLE, Book, Member  # noqa: E402

csv.field_size_limit(10**9)

SECTIONS = {"L": "Lending", "C": "Children", "B": "Buddhist", "R": "Reference"}
PLACEHOLDER = "Click on the box with a red arrow to enter"
NO_TITLE = "[No title in old system]"
TODAY = date.today()
NOW = datetime.now()

report = []  # (kind, old record no, key, detail)


def c(v):
    """Trimmed text with runs of whitespace collapsed."""
    return re.sub(r"\s+", " ", (v or "").replace("\x00", "")).strip()


def val(v):
    v = c(v)
    return "" if v in ("-", ".", PLACEHOLDER) else v


def parse_date(v, earliest=1900):
    """2008.01.26 / 20080623 -> date, anything else -> None."""
    digits = re.sub(r"\D", "", val(v))
    if len(digits) != 8:
        return None
    try:
        d = date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))
    except ValueError:
        return None
    return d if earliest <= d.year <= TODAY.year + 10 else None


def fit(value, limit, label, notes):
    """Cut a value to the column size; the full value is kept in the notes."""
    if len(value) <= limit:
        return value
    notes.append(f"Full old {label}: {value}")
    return value[:limit].strip()


def carets_to(v, sep):
    """ISIS subfields: '^nGodage^pKolamba' -> 'Godage, Kolamba'."""
    parts = [p.strip() for p in re.split(r"\^[A-Za-z]", val(v))]
    return sep.join(p for p in parts if p)


def title_text(v):
    """'Title^oOther title' -> 'Title : Other title'."""
    return c(re.sub(r"\s*\^[oO]\s*", " : ", val(v))).strip(" :")


def persons_text(v):
    out = []
    for part in val(v).split("~"):
        name, _, role = part.partition("^r")
        name, role = name.strip(), role.strip()
        if name:
            out.append(f"{name} ({role})" if role else name)
    return "; ".join(out)


def rows(folder, name):
    with open(os.path.join(folder, name), encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def check_lengths(table, records):
    limits = {col.name: col.type.length for col in table.columns
              if isinstance(col.type, String) and col.type.length}
    for rec in records:
        for k, n in limits.items():
            if len(rec[k]) > n:
                raise SystemExit(f"{table.name}.{k} too long ({len(rec[k])} > {n}): {rec[k]!r}")


# ---------------------------------------------------------------- members
def member_name(raw, notes):
    s = val(raw)
    name, sep, rest = s.partition("^")
    if not sep:
        return s
    if rest[:1] == "r":
        rest = rest[1:]
    m = re.match(r"^([^\s(*\-,]*)\s*([*\-,]*)\s*(.*)$", rest.strip())
    title, mark, extra = m.group(1), m.group(2).strip(","), m.group(3).strip()
    if mark:
        notes.append(f"Old system mark after the name: {mark}")
    out = name.strip()
    if title:
        out += f" ({title})"
    if extra:
        out += f" {extra}"
    return out


def member_type(raw, birthday, notes):
    t = val(raw).lower()
    if "bhikku" in t or "sister" in t:
        notes.append(f"Old membership type: {val(raw)}")
    if "life" in t:
        return "LIFETIME"
    if "ren" in t or "child" in t:
        return "CHILD"
    if t.startswith("ad") or "bhikku" in t:
        return "ADULT"
    age = (TODAY - birthday).days // 365 if birthday else None
    kind = "CHILD" if age is not None and age < 18 else "ADULT"
    notes.append(f"Membership type was not recorded in the old system ('{val(raw)}'); set to {kind.title()}")
    return kind


def build_member(r):
    notes = []
    name = member_name(r["10_member_name"], notes)

    birthday = parse_date(r["20_birthday"])
    if val(r["20_birthday"]) and not birthday:
        notes.append(f"Old birthday value: {val(r['20_birthday'])}")
    registered = parse_date(r["61_date"], earliest=1950)
    if val(r["61_date"]) and not registered:
        notes.append(f"Old registration date value: {val(r['61_date'])}")
    renewals = [d for d in (parse_date(x) for x in r["62_mebership_renewal_date"].split("~")) if d]

    kind_raw = r["35_membership_type"]
    on_loan = [a.strip() for a in val(r["40_acc_no"]).split("~") if a.strip()]
    if on_loan and not any(ch.isdigit() for ch in "".join(on_loan)):
        if not val(kind_raw) or parse_date(kind_raw):
            kind_raw = on_loan[0]  # the type was typed into the Acc. No. field
        on_loan = []
    kind = member_type(kind_raw, birthday, notes)
    if on_loan:
        notes.append(f"Old system: books on loan Acc. No. {', '.join(on_loan)}")

    nic = val(r["11_nic_no"])
    if len(nic) > 20:
        notes.append(f"Old NIC field: {nic}")
        nic = ""

    phones = [p.strip() for p in val(r["60_telephone_no"]).split("~") if p.strip()]
    telephone = ", ".join(phones)
    if len(telephone) > 30:
        notes.append(f"All telephone numbers: {telephone}")
        while phones and len(", ".join(phones)) > 30:
            phones.pop()
        telephone = ", ".join(phones) or telephone[:30]

    g_name, _, g_address = val(r["70_guarantor_name_address"]).partition("~")

    return {
        "membership_no": val(r["30_membership_no"]),
        "name": name,
        "address": val(r["1_address"]),
        "nic_no": nic,
        "birthday": birthday,
        "membership_type": kind,
        "email": "",
        "telephone": telephone,
        "registered_date": registered,
        "expiry_date": parse_date(r["59_expiry_date"]),
        "renewal_date": renewals[-1] if renewals else None,
        "guarantor_name": fit(g_name.strip(), 200, "guarantor", notes),
        "guarantor_address": g_address.strip(),
        "school": fit(val(r["80_school"]), 200, "school", notes),
        "notes": "\n".join(notes),
        "is_active": True,
        "created_at": NOW,
    }


def load_members(folder, existing):
    out, skipped = [], 0
    seen = set(existing)
    for r in rows(folder, "userdb_flat.csv"):
        m = build_member(r)
        key = m["membership_no"].upper()
        if not m["name"] or not key:
            report.append(("member skipped: no name or Membership No", r["mfn"], m["membership_no"], m["name"]))
            continue
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        out.append(m)
    return out, skipped


# ---------------------------------------------------------------- books
def section_of(raw, remarks):
    v = val(raw)
    letters = re.sub(r"[^A-Z]", "", v.upper())
    kinds = set(letters)
    if len(kinds) == 1 and letters[0] in SECTIONS:
        return SECTIONS[letters[0]]
    if not v:
        return ""
    remarks.append(f"Old section code: {v}")
    if "R" in kinds and kinds <= set(SECTIONS):
        return "Reference"  # e.g. B/R: keep it non-lending
    return ""


def price_of(raw):
    """'Rs. 250.00' -> (250.0, ''), 'Gift ~ Rs.35.00' -> (35.0, 'Gift'), 'Lak Saviya' -> (None, 'Lak Saviya')."""
    v = val(raw)
    m = re.search(r"\d[\d,]*(?:\.\d+)?", v)
    amount = None
    rest = v
    if m:
        try:
            amount = float(m.group().replace(",", ""))
        except ValueError:
            amount = None
        if amount is not None and 0 < amount < 1_000_000:
            rest = v[:m.start()] + " " + v[m.end():]
        else:
            amount = None
    rest = re.sub(r"(?i)\brs\b\.?", " ", rest)
    rest = re.sub(r"/[=\-]", " ", rest)
    return amount, c(rest).strip(" ~-().,;:/=")


def language_of(raw):
    v = val(raw)
    return {"sinhala": "Sinhala", "eng": "English", "english": "English"}.get(v.lower(), v)


def _date(y, m, d):
    try:
        x = date(y, m, d)
    except ValueError:
        return None
    return x if 2000 <= y and x <= TODAY else None


def date_candidates(raw):
    """'Date entered' was typed as YYYYMMDD, or with six digits as YYMMDD, DDMMYY or YYYYMM.

    Returns every reading that is a real date (no duplicates), most common form first.
    """
    digits = re.sub(r"\D", "", val(raw))
    if len(digits) == 8:
        found = [_date(int(digits[:4]), int(digits[4:6]), int(digits[6:]))]
    elif len(digits) == 6:
        a, b, e = int(digits[:2]), int(digits[2:4]), int(digits[4:])
        found = [_date(2000 + a, b, e), _date(2000 + e, b, a), _date(a * 100 + b, e, 1)]
    else:
        found = []
    return list(dict.fromkeys(d for d in found if d))


def entered_date(raw, near_year, remarks):
    """Six digits that can be read in more than one way are decided by the year of the
    neighbouring records (near_year); the typed value is then kept in the remarks."""
    v = val(raw)
    if not v:
        return None
    found = date_candidates(v)
    if len(found) == 1 and len(re.sub(r"\D", "", v)) == 8:
        return found[0]
    remarks.append(f"Old 'date entered' value: {v}")
    if not found:
        return None
    if near_year is None:
        return found[0]
    return min(found, key=lambda d: abs(d.year - near_year))


def year_finder(records):
    """Returns f(mfn) -> typical year of the neighbouring records whose date has only one reading."""
    import bisect
    from statistics import median
    known = []
    for r in records:
        found = date_candidates(r["22_date_entered"])
        if len(found) == 1:
            known.append((int(r["mfn"]), found[0].year))
    known.sort()
    keys = [k for k, _ in known]

    def near(mfn):
        i = bisect.bisect_left(keys, int(mfn))
        around = [y for _, y in known[max(0, i - 5):i + 5]]
        return round(median(around)) if around else None

    return near


def build_book(r, near_year):
    remarks = [x for x in (val(r["14_remarks"]), val(r["500_notes_informal"])) if x]

    title = title_text(r["200_title"])
    heading = title_text(r["190_heading"]).replace(" ~ ", "; ")
    if not title:
        if val(r["201_sinhala_title"]):
            title, source = title_text(r["201_sinhala_title"]), "the Sinhala title field"
        elif "T" in r["3_heading_identifier"].upper() and heading:
            title, source = heading, "the heading"
        else:
            title, source = NO_TITLE, ""
        remarks.append("Title was empty in the old system" + (f"; taken from {source}" if source else ""))
        report.append(("book had no title", r["mfn"], val(r["820_acc_no"]), title))

    if language_of(r["40_v40"]):
        remarks.append(f"Language: {language_of(r['40_v40'])}")

    p13, t13 = price_of(r["13_price"])
    p852, t852 = price_of(r["852_v852"])
    p836, t836 = price_of(r["836_v836"])
    price = next((p for p in (p13, p852, p836) if p is not None), 0)
    others = sorted({p for p in (p13, p852, p836) if p is not None and p != price})
    if others:
        remarks.append("Other price in old record: " + ", ".join(f"Rs. {p:.2f}" for p in others))
    sources = list(dict.fromkeys(t for t in (t13, t852, t836) if t))
    if sources:
        remarks.append("Source / price note: " + ", ".join(sources))

    entered = entered_date(r["22_date_entered"], near_year(r["mfn"]), remarks)
    if val(r["910_date_borrowed"]) or val(r["920_due_date"]):
        remarks.append(f"Old system loan fields: borrowed {val(r['910_date_borrowed']) or '-'}, "
                       f"due {val(r['920_due_date']) or '-'}")

    keywords = [k.strip() for k in val(r["620_keywords"]).split("~") if k.strip()]
    kw = [fit(k, 200, "keyword", remarks) for k in keywords[:3]] + [""] * 3
    more = keywords[3:]
    kept = list(more)
    while kept and len("; ".join(kept)) > 200:
        kept.pop()
    if len(kept) < len(more):
        remarks.append("More keywords: " + "; ".join(more[len(kept):]))

    section = section_of(r["15_section"], remarks)
    code = lambda v: re.sub(r"[<>]", "", val(v))  # noqa: E731

    book = {
        "acc_no": val(r["820_acc_no"]),
        "title": title,
        "sinhala_title": title_text(r["201_sinhala_title"]),
        "tamil_title": title_text(r["203_tamil_title"]),
        "sinhala_title_formal": "",
        "parent_title": title_text(r["202_parent_title"]),
        "parent_title_2": "",
        "persons": persons_text(r["300_person_s"]),
        "corporate_body": carets_to(r["310_corporate_body"], ", "),
        "meeting": carets_to(r["320_meeting"], ", "),
        "edition": fit(val(r["260_edition"]), 100, "edition", remarks),
        "publisher": carets_to(r["400_publisher"], ", "),
        "year_of_publication": fit(val(r["440_year_of_publication"]), 20, "year of publication", remarks),
        "physical_description": carets_to(r["460_physical_description"], " : "),
        "series": val(r["480_series"]),
        "citation": val(r["490_citation"]),
        "isbn": fit(val(r["100_isbn"]), 30, "ISBN", remarks),
        "issn": fit(val(r["101_issn"]), 30, "ISSN", remarks),
        "record_type": fit(code(r["1_record_type"]), 100, "record type", remarks),
        "bibliographic_level": fit(code(r["2_bibliographic_level"]), 100, "bibliographic level", remarks),
        "item_identifier": fit(code(r["4_item_identifier"]), 100, "item identifier", remarks),
        "medium": fit(val(r["11_medium"]), 100, "medium", remarks),
        "heading_identifier": fit(code(r["3_heading_identifier"]), 100, "heading identifier", remarks),
        "heading": heading,
        "material_type": fit(val(r["60_type_of_material"]), 100, "type of material", remarks),
        "section": section,
        "price": Decimal(f"{price:.2f}"),
        "date_entered": entered,
        "class_no_scheme": fit(val(r["610_classi_no_scheme"]), 100, "class no", remarks),
        "call_no": fit(val(r["810_call_no"]), 100, "call no", remarks),
        "keyword_1": kw[0],
        "keyword_2": kw[1],
        "keyword_3": kw[2],
        "keyword_4": "; ".join(kept),
        "notes_bib": val(r["510_notes_bib_re"]),
        "notes_contents": val(r["530_notes_contents"]),
        "abstracts": val(r["600_abstracts"]),
        "broad_headings": val(r["615_broad_heading_s_notation"]),
        "geographical_code": fit(val(r["625_geographical_code"]), 50, "geographical code", remarks),
        "entered_by": fit(val(r["871_entered_by"]), 100, "entered by", remarks),
        "user_code": fit(val(r["900_user_code"]), 50, "user code", remarks),
        "rack_no": "",
        "shelf_no": "",
        "status": AVAILABLE,
        "withdrawn": False,
        "withdrawn_by": "",
        "withdrawn_date": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    return book, remarks


def load_books(folder, existing):
    """existing: {ACC NO upper: title} of books already in the database."""
    out, stats = [], Counter()
    taken = {k: {"title": t, "mfn": "", "print": None, "remarks": None, "matched": False}
             for k, t in existing.items()}
    records = list(rows(folder, "libcat_flat.csv"))
    near_year = year_finder(records)
    for r in records:
        if not val(r["200_title"]) and not val(r["820_acc_no"]):
            stats["blank"] += 1
            report.append(("book skipped: no title and no Acc. No.", r["mfn"], "", val(r["190_heading"])))
            continue
        fingerprint = tuple(c(v) for k, v in r.items() if k != "mfn")
        book, remarks = build_book(r, near_year)
        acc = book["acc_no"]
        if not acc:
            acc = book["acc_no"] = f"NOACC-{r['mfn']}"
            remarks.append("No Acc. No. in the old system; a temporary one was given")
            report.append(("book had no Acc. No.", r["mfn"], acc, book["title"]))
            stats["no_acc"] += 1
        first = taken.get(acc.upper())
        if first:
            if first["print"] is None and not first["matched"] and first["title"] == book["title"]:
                first["matched"] = True
                stats["already_in_database"] += 1
                continue
            if first["print"] == fingerprint:
                stats["exact_duplicate"] += 1
                report.append(("book skipped: exact duplicate record", r["mfn"], acc,
                               f"same as old record {first['mfn']}: {book['title']}"))
                continue
            n = 2
            while f"{acc}-D{n}".upper() in taken:
                n += 1
            new_acc = f"{acc}-D{n}"
            remarks.append(f"Acc. No. {acc} was already used by another book in the old system "
                           f"(old record {first['mfn'] or 'already imported'}); stored as {new_acc}")
            if first["remarks"] is not None:
                first["remarks"].append(f"Acc. No. {acc} was also used by old record {r['mfn']} (stored as {new_acc})")
            report.append(("duplicate Acc. No.", r["mfn"], new_acc,
                           f"{acc} is used by old record {first['mfn'] or '(already imported)'} \"{first['title']}\""
                           f" and by this record \"{book['title']}\""))
            stats["duplicate_acc_renamed"] += 1
            acc = book["acc_no"] = new_acc
        taken[acc.upper()] = {"title": book["title"], "mfn": r["mfn"], "print": fingerprint,
                              "remarks": remarks, "matched": True}
        out.append((book, remarks))
    books = []
    for book, remarks in out:
        book["remarks"] = "; ".join(remarks)
        books.append(book)
    return books, stats


# ---------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) != 1:
        raise SystemExit(__doc__)
    folder = args[0]

    with engine.begin() as conn:
        have_members = {m.upper() for (m,) in conn.execute(select(Member.membership_no))}
        have_books = {a.upper(): t for a, t in conn.execute(select(Book.acc_no, Book.title))}

        members, m_skipped = load_members(folder, have_members)
        books, stats = load_books(folder, have_books)
        check_lengths(Member.__table__, members)
        check_lengths(Book.__table__, books)

        print(f"members to insert: {len(members)}  (already in database: {m_skipped})")
        print("  types:", dict(Counter(m["membership_type"] for m in members)))
        print("  without registration date:", sum(m["registered_date"] is None for m in members),
              "| without birthday:", sum(m["birthday"] is None for m in members),
              "| with expiry date:", sum(m["expiry_date"] is not None for m in members),
              "| with notes:", sum(bool(m["notes"]) for m in members))
        print(f"books to insert: {len(books)}  {dict(stats)}")
        print("  sections:", dict(Counter(b["section"] for b in books)))
        print("  with price:", sum(b["price"] > 0 for b in books),
              "| without date entered:", sum(b["date_entered"] is None for b in books),
              "| date entered by year:", sorted(Counter(b["date_entered"].year for b in books if b["date_entered"]).items()),
              "| placeholder title:", sum(b["title"] == NO_TITLE for b in books))
        print("  report lines:", dict(Counter(k for k, *_ in report)))

        with open(os.path.join(folder, "import_report.csv"), "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["what", "old record no (MFN)", "Membership No / Acc. No.", "detail"])
            w.writerows(report)

        if dry:
            samples = [m for m in members if m["notes"]][:6] + [b for b in books if "D2" in b["acc_no"]][:3]
            for s in samples:
                print("  e.g.", {k: str(v) for k, v in s.items() if v not in ("", None, False) and k not in ("created_at", "updated_at")})
            print("DRY RUN - nothing was written.")
            conn.rollback()
            return

        if engine.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE members ALTER COLUMN registered_date DROP NOT NULL"))
        for table, records in ((Member.__table__, members), (Book.__table__, books)):
            for i in range(0, len(records), 1000):
                conn.execute(insert(table), records[i:i + 1000])
        print("totals now:", conn.execute(text("select count(*) from members")).scalar(), "members,",
              conn.execute(text("select count(*) from books")).scalar(), "books")
    print("DONE - committed.")


main()
