CREATE TABLE IF NOT EXISTS dvs.h_people (
    hk_person_id VARCHAR(32) NOT NULL,
    person_id INT NOT NULL,
    registration_date TIMESTAMP,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL,
    CONSTRAINT pk_h_people PRIMARY KEY (hk_person_id) DISABLED
) ORDER BY person_id SEGMENTED BY HASH(hk_person_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.h_groups (
    hk_group_id VARCHAR(32) NOT NULL,
    group_id INT NOT NULL,
    created_date TIMESTAMP,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL,
    CONSTRAINT pk_h_groups PRIMARY KEY (hk_group_id) DISABLED
) ORDER BY group_id SEGMENTED BY HASH(hk_group_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.h_chats (
    hk_msg_id VARCHAR(32) NOT NULL,
    msg_id INT NOT NULL,
    msg_time TIMESTAMP(6),
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL,
    CONSTRAINT pk_h_chats PRIMARY KEY (hk_msg_id) DISABLED
) ORDER BY msg_id SEGMENTED BY HASH(hk_msg_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.l_chat_owners (
    hk_l_chat_owner_id VARCHAR(32) NOT NULL,
    hk_person_id VARCHAR(32) NOT NULL,
    hk_group_id VARCHAR(32) NOT NULL,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL,
    CONSTRAINT pk_l_chat_owners PRIMARY KEY (hk_l_chat_owner_id) DISABLED
) ORDER BY hk_group_id SEGMENTED BY HASH(hk_l_chat_owner_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.l_person_chat (
    hk_l_person_chat_id VARCHAR(32) NOT NULL,
    hk_person_id VARCHAR(32) NOT NULL,
    hk_msg_id VARCHAR(32) NOT NULL,
    participant_role VARCHAR(4) NOT NULL,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL,
    CONSTRAINT pk_l_person_chat PRIMARY KEY (hk_l_person_chat_id) DISABLED
) ORDER BY hk_msg_id SEGMENTED BY HASH(hk_l_person_chat_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.l_groups (
    hk_l_group_id VARCHAR(32) NOT NULL,
    hk_msg_id VARCHAR(32) NOT NULL,
    hk_group_id VARCHAR(32) NOT NULL,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL,
    CONSTRAINT pk_l_groups PRIMARY KEY (hk_l_group_id) DISABLED
) ORDER BY hk_msg_id SEGMENTED BY HASH(hk_l_group_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.s_person_info (
    hk_person_id VARCHAR(32) NOT NULL,
    name VARCHAR(256),
    date_of_birthday DATE,
    country VARCHAR(128),
    phone VARCHAR(32),
    e_mail VARCHAR(256),
    hash_diff VARCHAR(32) NOT NULL,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL
) ORDER BY hk_person_id, load_date SEGMENTED BY HASH(hk_person_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.s_group_info (
    hk_group_id VARCHAR(32) NOT NULL,
    title VARCHAR(256),
    status VARCHAR(32),
    hash_diff VARCHAR(32) NOT NULL,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL
) ORDER BY hk_group_id, load_date SEGMENTED BY HASH(hk_group_id) ALL NODES;

CREATE TABLE IF NOT EXISTS dvs.s_chat_info (
    hk_msg_id VARCHAR(32) NOT NULL,
    text_msg VARCHAR(4096),
    status VARCHAR(32),
    hash_diff VARCHAR(32) NOT NULL,
    source VARCHAR(64),
    load_date TIMESTAMP NOT NULL
) ORDER BY hk_msg_id, load_date SEGMENTED BY HASH(hk_msg_id) ALL NODES;
