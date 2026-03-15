import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free'")
cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100)")
conn.commit()
cur.close()
conn.close()
print('Done!')