#!/usr/bin/env python3
"""
Word文档中文翻译英文版（独立使用，不依赖OCR）

复用 ocr_translate.py 中的翻译函数，通过 import 调用
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile

# 复用 ocr_translate.py 中的翻译函数
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from ocr_translate import (
    extract_chinese_texts,
    translate_xml_file,
    translate_word,
)


def main():
    parser = argparse.ArgumentParser(description='Word文档中文翻译英文版')
    parser.add_argument('input', help='输入Word文档')
    parser.add_argument('-o', '--output', help='输出Word文档')
    parser.add_argument('--extract', action='store_true', help='提取中文文本')
    parser.add_argument('--apply', metavar='JSON', help='应用翻译JSON文件')
    parser.add_argument('--work-dir', default='./temp_translate')
    args = parser.parse_args()

    input_path = args.input
    output_path = args.output or input_path.replace('.docx', '_en.docx')
    work_dir = args.work_dir

    if args.extract:
        with zipfile.ZipFile(input_path, 'r') as z:
            all_texts = set()
            for name in z.namelist():
                if name.endswith('.xml'):
                    texts = extract_chinese_texts(z.read(name).decode('utf-8'))
                    all_texts.update(texts)

        os.makedirs(work_dir, exist_ok=True)
        texts_file = os.path.join(work_dir, 'texts_to_translate.json')
        with open(texts_file, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(all_texts)), f, ensure_ascii=False, indent=2)

        print(f"提取 {len(all_texts)} 条中文 -> {texts_file}")

    elif args.apply:
        with open(args.apply, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        translations = {k: v for k, v in translations.items() if v}

        translate_word(input_path, translations, output_path, work_dir)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
