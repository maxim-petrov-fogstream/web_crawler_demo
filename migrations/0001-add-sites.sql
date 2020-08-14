BEGIN;
CREATE TABLE `tp_site` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `name` varchar(255) NOT NULL,
    `url` varchar(200) NOT NULL
)
;

INSERT INTO `tp_site` (`name`, `url`) VALUES ('Технопоинт', 'http://technopoint.ru');

ALTER TABLE `tp_catalog`
      ADD COLUMN `site_id` integer NOT NULL DEFAULT 1,
      ADD CONSTRAINT `site_id_refs_id_b4fc1586` FOREIGN KEY (`site_id`) REFERENCES `tp_site` (`id`);
COMMIT;
