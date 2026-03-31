import sqlite3

# Let's start with a simpler SQLite for local dev
conn = sqlite3.connect('manga.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS manga (id INTEGER PRIMARY KEY, title TEXT, link TEXT)''')
conn.commit()
conn.close()
print("DB test OK")
