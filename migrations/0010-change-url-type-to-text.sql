ALTER TABLE tp_catalog MODIFY url TEXT;
DROP INDEX sid_id ON tp_product;
ALTER TABLE tp_product MODIFY tpid TEXT;
CREATE INDEX sid_id ON tp_product (sid_id, tpid(255));
