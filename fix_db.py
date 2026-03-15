import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(100)')
cur.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP')
conn.commit()
cur.close()
conn.close()
print('Done!')