BEGIN;
ALTER TABLE `tp_site` ADD COLUMN `parser` varchar(255) NOT NULL DEFAULT 'technopoint';
COMMIT;
