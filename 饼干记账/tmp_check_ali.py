import sqlite3
db = r'D:\2Study\StudyNotes\.db\biscuit_accountant.db'
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT id,time,amount,account,note FROM bills WHERE note LIKE '%阿里健康%' OR note LIKE '%冈本%' ORDER BY time DESC LIMIT 5")
for r in cur.fetchall():
    print(r)