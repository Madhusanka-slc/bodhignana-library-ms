# Sample data in the library database

The library database holds the **real** catalogue and member list imported from the old J-ISIS
system (10,229 members, 55,161 books). On 7 October 2026 a small amount of **sample data** was added
on top of it, only to show how the screens look with loans, fines and today's counts.

Everything below is sample data. Nothing else in the database is.
To remove all of it, run [remove_sample_data.sql](remove_sample_data.sql) (see the end of this file).

## How to recognise it

- Sample loans: `loans.notes = 'SAMPLE DATA'`
- Sample payments: `payments.notes` starts with `SAMPLE DATA`
- Sample members: name starts with `SAMPLE - ` and `notes = 'SAMPLE DATA'`
- Sample books: title starts with `SAMPLE - ` and `remarks = 'SAMPLE DATA'`

Before the sample data was added there were **no** loans and **no** payments in the database.

## Sample members (created 2026-10-07)

| id | Membership No | Name |
|---|---|---|
| 10230 | M10230 | SAMPLE - Perera, Nimal (Mr.) |
| 10231 | M10231 | SAMPLE - Silva, Kavindi (Ms.) |
| 10232 | M10232 | SAMPLE - Wizard, Test (Ms.) (made while testing the step-by-step New member form) |

The three sample members also have **sample photos** (a plain drawn silhouette marked "SAMPLE PHOTO"),
stored in the `photos` Docker volume as `/app/data/photos/10230-*.jpg` to `10232-*.jpg`.
No real member has a photo yet.

## Sample books (created 2026-10-07)

| id | Acc. No. | Title |
|---|---|---|
| 55162 | B055162 | SAMPLE - Madol Duwa |
| 55163 | B055163 | SAMPLE - Gamperaliya |
| 55164 | B055164 | SAMPLE - Hathpana |
| 55165 | B055165 | SAMPLE - Wizard test book (made while testing the step-by-step New book form) |
| 55166 | B055166 | SAMPLE - Wizard test book (its "Add another copy", same test) |

The three sample books also have **sample cover pictures** (drawn by a script, marked "SAMPLE COVER"),
stored in the `covers` Docker volume as `/app/data/covers/55162-*.jpg` to `55166-*.jpg`
(books 55165 and 55166 use a copy of the Madol Duwa sample cover).
No real book has a cover picture yet.

## Sample loans (real books lent to real members, all made up)

These use **real** books and **real** members, so removing them must also put the books back to
"In library". The removal script does that.

| loan id | book id | Acc. No. | Member No | Issued | Due | Returned | Book status now |
|---|---|---|---|---|---|---|---|
| 6 | 40561 | 1634 | 9244 | 2026-09-15 | 2026-09-29 | | ISSUED (overdue) |
| 7 | 34448 | 260 | 7635 | 2026-09-12 | 2026-09-26 | | ISSUED (overdue) |
| 8 | 51037 | 67D | 7635 | 2026-09-12 | 2026-09-26 | | ISSUED (overdue) |
| 9 | 39967 | 407 | 8784 | 2026-09-09 | 2026-09-23 | | ISSUED (overdue) |
| 10 | 50309 | 662 | 9621 | 2026-09-04 | 2026-09-18 | | ISSUED (overdue) |
| 11 | 50623 | 18D | 9685 | 2026-08-30 | 2026-09-14 | | ISSUED (overdue) |
| 12 | 54986 | 592 | 9685 | 2026-08-30 | 2026-09-14 | | ISSUED (overdue) |
| 13 | 54830 | 630 | 7749 | 2026-08-23 | 2026-09-07 | | ISSUED (overdue) |
| 14 | 50783 | 308D | 1494 | 2026-08-17 | 2026-08-31 | | ISSUED (overdue) |
| 15 | 44836 | 587 | 9292 | 2026-10-06 | 2026-10-20 | | ISSUED |
| 16 | 54906 | 632 | 8803 | 2026-10-03 | 2026-10-17 | | ISSUED |
| 17 | 33876 | 286 | 7636 | 2026-09-30 | 2026-10-14 | | ISSUED |
| 18 | 40516 | 1584 | 7509 | 2026-09-27 | 2026-10-12 | | ISSUED |
| 19 | 55077 | 393 | 9163 | 2026-08-08 | 2026-08-22 | 2026-09-07 | in library (fine unpaid) |
| 20 | 51209 | 57D | 7269 | 2026-08-13 | 2026-08-27 | 2026-09-16 | in library (fine unpaid) |
| 21 | 44230 | 3013 | 10 | 2026-08-20 | 2026-09-03 | 2026-09-25 | in library (fine unpaid) |
| 22 | 41677 | 32 | 7499 | 2026-08-28 | 2026-09-11 | 2026-10-07 | in library (fine paid) |
| 23 | 34058 | 1994 | 9238 | 2026-09-07 | 2026-09-21 | 2026-10-07 | in library (fine paid) |
| 24 | 41670 | 3572 | 9689 | 2026-09-17 | 2026-10-01 | 2026-09-28 | in library |
| 25 | 44034 | 3591 | 8801 | 2026-09-25 | 2026-10-09 | 2026-10-05 | in library |
| 26 | 48018 | 73631 | 10231 | 2026-10-07 | 2026-10-21 | | ISSUED |
| 27 | 47984 | 71091 | 9604 | 2026-10-07 | 2026-10-21 | | ISSUED |

## Sample staff account (created 2026-10-08)

| id | Sign-in name | Password | Name | Role |
|---|---|---|---|---|
| 2 | sample.staff | staff123 | SAMPLE - Staff User | Staff |

To show who-did-what tracking, this staff user issued and returned sample book B055166 to sample member
M10230 (loan **28**) and took a Rs. 20.00 payment from M10230 (payment **4**, receipt R2026-000003).
These, and the activity-log lines about all sample records, are removed by the script.

## Sample payments

| id | loan id | Receipt | Amount |
|---|---|---|---|
| 2 | 22 | R2026-000001 | Rs. 40.00 |
| 3 | 23 | R2026-000002 | Rs. 24.00 |
| 4 | - (member M10230) | R2026-000003 | Rs. 20.00 (taken by the sample staff user) |

## Removing the sample data

From the `library-system` folder:

```
docker compose exec -T db psql -U library -d library -f - < scripts/sample_data/remove_sample_data.sql
```

The script works by the exact ids listed above, inside one transaction, and refuses to run if any of
those rows no longer look like sample data. After it runs, receipt numbers start again from
R2026-000001.

Then delete the sample member photo files:

```
docker compose exec backend sh -c "rm -f /app/data/photos/10230-*.jpg /app/data/photos/10231-*.jpg /app/data/photos/10232-*.jpg"
```

and the sample cover picture files:

```
docker compose exec backend sh -c "rm -f /app/data/covers/55162-*.jpg /app/data/covers/55163-*.jpg /app/data/covers/55164-*.jpg /app/data/covers/55165-*.jpg /app/data/covers/55166-*.jpg"
```
