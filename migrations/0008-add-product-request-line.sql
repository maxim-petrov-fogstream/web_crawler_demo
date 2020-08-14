BEGIN;

ALTER TABLE `tp_product`
      ADD COLUMN `request_line` LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '';

COMMIT
