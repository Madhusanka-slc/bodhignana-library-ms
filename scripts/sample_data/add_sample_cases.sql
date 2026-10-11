-- Sample cases on REAL books and members, added 2026-10-08 (see SAMPLE_DATA.md, "Sample cases").
-- Shows every kind of book / member state on the screens. remove_sample_data.sql undoes all of it.
-- Run:  docker compose exec -T db psql -U library -d library -f - < scripts/sample_data/add_sample_cases.sql
--
--   member 10217 (id 10226): 2 books now (29 on time, 30 overdue), returned damaged with unpaid damage fine (31),
--                            returned late with unpaid late fine (32), member card marked given
--   member 8967  (id 9001) : made "not active"
--   book 6834 (id 9)  : Damaged (returned damaged in loan 31)
--   book 5003 (id 10) : Lost
--   book 6854 (id 12) : Withdrawn
--   book 7329 (id 13) : in library with rack / shelf R3 / S2
--   book 6881 (id 15) : QR label marked done

\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM loans WHERE id BETWEEN 29 AND 32) THEN
    RAISE EXCEPTION 'A loan 29-32 already exists - stopping, nothing added';
  END IF;
  IF (SELECT count(*) FROM books WHERE id IN (7, 8, 9, 10, 12, 13, 15, 17) AND status = 'AVAILABLE' AND NOT withdrawn
        AND rack_no = '' AND shelf_no = '' AND NOT label_done) <> 8 THEN
    RAISE EXCEPTION 'A chosen book is not in its original state - stopping, nothing added';
  END IF;
  IF (SELECT count(*) FROM members WHERE id IN (9001, 10226) AND is_active AND NOT card_done) <> 2 THEN
    RAISE EXCEPTION 'A chosen member is not in its original state - stopping, nothing added';
  END IF;
END $$;

INSERT INTO loans (id, book_id, member_id, issue_date, due_date, return_date, issued_by, returned_by, is_damaged,
                   late_days, late_fine, damage_fine, notes, created_at, returned_at)
VALUES (29, 7,  10226, '2026-10-01', '2026-10-15', NULL,         'Administrator', '',              false, 0, 0,     0,      'SAMPLE DATA', now(), NULL),
       (30, 8,  10226, '2026-09-20', '2026-10-04', NULL,         'Administrator', '',              false, 0, 0,     0,      'SAMPLE DATA', now(), NULL),
       (31, 9,  10226, '2026-09-10', '2026-09-24', '2026-09-22', 'Administrator', 'Administrator', true,  0, 0,     500.00, 'SAMPLE DATA', now(), '2026-09-22 10:30'),
       (32, 17, 10226, '2026-09-01', '2026-09-15', '2026-09-25', 'Administrator', 'Administrator', false, 8, 12.00, 0,      'SAMPLE DATA', now(), '2026-09-25 11:15');
SELECT setval('loans_id_seq', greatest((SELECT max(id) FROM loans), 32));

UPDATE books SET status = 'ISSUED'  WHERE id IN (7, 8);
UPDATE books SET status = 'DAMAGED' WHERE id = 9;
UPDATE books SET status = 'LOST'    WHERE id = 10;
UPDATE books SET status = 'WITHDRAWN', withdrawn = true, withdrawn_by = 'Administrator', withdrawn_date = '2026-10-02' WHERE id = 12;
UPDATE books SET rack_no = 'R3', shelf_no = 'S2' WHERE id = 13;
UPDATE books SET label_done = true, label_done_at = now(), label_done_by = 'Administrator' WHERE id = 15;

UPDATE members SET is_active = false WHERE id = 9001;
UPDATE members SET card_done = true, card_done_at = now(), card_done_by = 'Administrator' WHERE id = 10226;

COMMIT;
