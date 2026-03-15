import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("UPDATE users SET plan = 'premium' WHERE email = 'tumhari_email@gmail.com'")
conn.commit()
cur.close()
conn.close()
print('Done!')