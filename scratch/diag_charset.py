import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'

import django
django.setup()

from django.db import connection
c = connection.cursor()

c.execute("SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=DATABASE()")
print("DB default:", c.fetchone())

c.execute("SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_NAME='auth_user' AND COLUMN_NAME='id'")
print("auth_user.id type:", c.fetchone())

c.execute("SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_NAME='auth_user'")
print("auth_user collation:", c.fetchone())

c.execute("SHOW VARIABLES LIKE 'character_set_connection'")
print("Connection charset:", c.fetchone())

c.execute("SHOW VARIABLES LIKE 'collation_connection'")
print("Connection collation:", c.fetchone())

# Try to create the table manually to see the actual SQL
c.execute("DROP TABLE IF EXISTS members_userprofile")
c.execute("""
    CREATE TABLE members_userprofile (
        id bigint AUTO_INCREMENT PRIMARY KEY,
        is_premium bool NOT NULL DEFAULT 0,
        premium_until datetime(6) NULL,
        created_at datetime(6) NOT NULL,
        user_id int NOT NULL,
        CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES auth_user(id)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
""")
print("Manual table creation: SUCCESS!")
c.execute("DROP TABLE members_userprofile")
