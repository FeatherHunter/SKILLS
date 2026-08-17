# -*- coding: utf-8 -*-
import re, json

html = open(r'D:\2Study\StudyNotes\.db\home_manager_html\查账号_20260814_114104.html', encoding='utf-8').read()
m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
if m:
    p = json.loads(m.group(1))
    print(json.dumps(p, ensure_ascii=False, indent=1)[:2500])
else:
    print('no payload found')
