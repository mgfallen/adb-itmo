CREATE TABLE IF NOT EXISTS marts.dm_person_activity (
    person_id INT,
    name VARCHAR(256),
    country VARCHAR(128),
    groups_owned INT,
    messages_sent INT,
    messages_received INT
) ORDER BY person_id;

CREATE TABLE IF NOT EXISTS marts.dm_group_activity (
    group_id INT,
    title VARCHAR(256),
    owner_id INT,
    messages_count INT,
    members_count INT
) ORDER BY group_id;

CREATE TABLE IF NOT EXISTS marts.dm_message_stats (
    stat_date DATE,
    messages_total INT,
    group_messages INT,
    private_messages INT,
    messages_with_link INT,
    avg_text_length NUMERIC(12, 2)
) ORDER BY stat_date;
