"""用 DAY14 素材测试 cover-composer"""
import sys
import os
sys.path.insert(0, r'D:\2Study\StudyNotes\SKILLS\封面合成')
sys.path.insert(0, r'D:\2Study\StudyNotes\SKILLS\封面合成\scripts')
sys.path.insert(0, r'D:\2Study\StudyNotes\SKILLS\封面合成\lib')

os.chdir(r'D:\2Study\StudyNotes\SKILLS\封面合成')

sys.argv = [
    'cover-composer', 'compose',
    '--photos',
    r'D:/Users/辰辰洋洋/Videos/素材/健身/DAY14/IMG_20260715_200954.jpg',
    r'C:/Users/辰辰洋洋/.mavis/v2/assets/2026/07/15/22-52-42-378-asset_20260715-225242-378_c0c835e9300a_202714d8-img_v3_0213k_f8f02c84-f67f-4b86-b4c4-a454a999214g.png',
    r'C:/Users/辰辰洋洋/.mavis/v2/assets/2026/07/15/22-53-32-971-asset_20260715-225332-971_8f264e11f018_15db3022-img_v3_0213k_6c84cb4b-eaa2-4d5a-a50d-8abb134b47bg.png',
    '--layout', 'symmetric-cascade',
    '--aspect', '16:9',
    '--text', '{"main":"14 天","sub":"-7 斤","tags":"腰突 大基数"}',
    '-o', r'D:/Users/辰辰洋洋/Videos/素材/健身/DAY14/cover_v16_skill.jpg',
]

from cli import main
try:
    main()
except SystemExit:
    pass
