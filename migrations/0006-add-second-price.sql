BEGIN;

ALTER TABLE `tp_product`
      ADD COLUMN `second_price` integer NULL;

COMMIT;
