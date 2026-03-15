import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS family_members (
        id SERIAL PRIMARY KEY,
        owner_id INTEGER REFERENCES users(id),
        member_id INTEGER REFERENCES users(id),
        relationship VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
    )
""")
conn.commit()
cur.close()
conn.close()
print('Done!')