CREATE TABLE IF NOT EXISTS staging.st_people (
    id INT,
    name VARCHAR(256),
    registration_date TIMESTAMP,
    country VARCHAR(128),
    date_of_birthday DATE,
    phone VARCHAR(32),
    e_mail VARCHAR(256)
);

CREATE TABLE IF NOT EXISTS staging.st_groups (
    id INT,
    owner_id INT,
    group_name VARCHAR(256),
    created_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staging.st_chats (
    msg_id INT,
    msg_time TIMESTAMP(6),
    msg_from INT,
    msg_to INT,
    text_msg VARCHAR(4096),
    msg_group_id INT
);
