BEGIN;
ALTER TABLE `tp_site`
      ADD COLUMN `active` bool NOT NULL DEFAULT TRUE;
COMMIT;
