-- Remove the sample data added on 2026-10-07 / 2026-10-08 (see SAMPLE_DATA.md).
-- Works only on the exact ids below; real library data is not touched.
-- Run:  docker compose exec -T db psql -U library -d library -f - < scripts/sample_data/remove_sample_data.sql

\set ON_ERROR_STOP on
BEGIN;

-- Safety check: every listed row must still be marked as sample data.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM loans WHERE id BETWEEN 6 AND 32 AND notes <> 'SAMPLE DATA') THEN
    RAISE EXCEPTION 'A listed loan is not marked SAMPLE DATA - stopping, nothing removed';
  END IF;
  IF EXISTS (SELECT 1 FROM payments WHERE id IN (2, 3, 4) AND notes NOT LIKE 'SAMPLE DATA%') THEN
    RAISE EXCEPTION 'A listed payment is not marked SAMPLE DATA - stopping, nothing removed';
  END IF;
  IF EXISTS (SELECT 1 FROM members WHERE id IN (10230, 10231, 10232) AND name NOT LIKE 'SAMPLE -%') THEN
    RAISE EXCEPTION 'A listed member is not a sample member - stopping, nothing removed';
  END IF;
  IF EXISTS (SELECT 1 FROM books WHERE id IN (55162, 55163, 55164, 55165, 55166) AND title NOT LIKE 'SAMPLE -%') THEN
    RAISE EXCEPTION 'A listed book is not a sample book - stopping, nothing removed';
  END IF;
  IF EXISTS (SELECT 1 FROM users WHERE id = 2 AND full_name NOT LIKE 'SAMPLE -%') THEN
    RAISE EXCEPTION 'User 2 is not the sample staff user - stopping, nothing removed';
  END IF;
END $$;

-- 1. Sample payments (linked to sample loans / sample member)
DELETE FROM payments WHERE id IN (2, 3, 4);

-- 2. Put the real books that were "lent" back on the shelf, unless a real loan has them now
UPDATE books b SET status = 'AVAILABLE'
WHERE b.id IN (40561, 34448, 51037, 39967, 50309, 50623, 54986, 54830, 50783,
               44836, 54906, 33876, 40516, 48018, 47984, 7, 8)
  AND b.status = 'ISSUED'
  AND NOT EXISTS (SELECT 1 FROM loans l WHERE l.book_id = b.id AND l.return_date IS NULL
                  AND l.id NOT BETWEEN 6 AND 32);

-- 2b. Put the real books and members used for the "sample cases" back as they were
--     (all of them were In library, not withdrawn, no rack / shelf, no QR label mark; both members active, no card mark)
UPDATE books SET status = 'AVAILABLE' WHERE id IN (9, 10) AND status IN ('DAMAGED', 'LOST');
UPDATE books SET status = 'AVAILABLE', withdrawn = false, withdrawn_by = '', withdrawn_date = NULL WHERE id = 12 AND status = 'WITHDRAWN';
UPDATE books SET rack_no = '', shelf_no = '' WHERE id = 13 AND rack_no = 'R3' AND shelf_no = 'S2';
UPDATE books SET label_done = false, label_done_at = NULL, label_done_by = '' WHERE id = 15;
UPDATE members SET is_active = true WHERE id = 9001;
UPDATE members SET card_done = false, card_done_at = NULL, card_done_by = '' WHERE id = 10226;

-- 3. Sample loans
DELETE FROM loans WHERE id BETWEEN 6 AND 32 AND notes = 'SAMPLE DATA';

-- 4. Sample members and books (only if nothing real refers to them)
DELETE FROM members m WHERE m.id IN (10230, 10231, 10232)
  AND NOT EXISTS (SELECT 1 FROM loans l WHERE l.member_id = m.id)
  AND NOT EXISTS (SELECT 1 FROM payments p WHERE p.member_id = m.id);
DELETE FROM books b WHERE b.id IN (55162, 55163, 55164, 55165, 55166)
  AND NOT EXISTS (SELECT 1 FROM loans l WHERE l.book_id = b.id);

-- 5. Activity log lines about the sample records, and everything the sample staff user did
DELETE FROM audit_log
WHERE user_id = 2
   OR (entity = 'user' AND entity_id = 2)
   OR (entity = 'loan' AND entity_id BETWEEN 6 AND 32)
   OR (entity = 'payment' AND entity_id IN (2, 3, 4))
   OR (entity = 'member' AND entity_id IN (10230, 10231, 10232))
   OR (entity = 'book' AND entity_id IN (55162, 55163, 55164, 55165, 55166));

-- 6. The sample staff account (sign-in name sample.staff)
DELETE FROM users WHERE id = 2 AND full_name LIKE 'SAMPLE -%';

SELECT (SELECT count(*) FROM loans WHERE notes = 'SAMPLE DATA') AS sample_loans_left,
       (SELECT count(*) FROM members WHERE name LIKE 'SAMPLE -%') AS sample_members_left,
       (SELECT count(*) FROM books WHERE title LIKE 'SAMPLE -%') AS sample_books_left,
       (SELECT count(*) FROM users WHERE full_name LIKE 'SAMPLE -%') AS sample_users_left,
       (SELECT count(*) FROM books WHERE status = 'ISSUED') AS books_still_issued;

COMMIT;
