import sqlite3
db = r'D:\2Study\StudyNotes\.db\biscuit_accountant.db'
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT id,time,amount,account,note FROM bills WHERE note LIKE '%高德打车%' ORDER BY time")
for r in cur.fetchall():
    print(r)
