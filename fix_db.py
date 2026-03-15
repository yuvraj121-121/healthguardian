import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()
cur.execute("UPDATE users SET plan = 'premium' WHERE email = 'yuvrajbasnet1234@gmail.com'")
conn.commit()

# Verify karo
cur.execute("SELECT email, plan FROM users")
rows = cur.fetchall()
for row in rows:
    print(row)
cur.close()
conn.close()