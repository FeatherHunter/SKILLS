#!/usr/bin/env python3
"""
一键完成：PDF OCR识别 + 中文Word翻译英文版

复用官方 ocr-skill/scripts/pdf_ocr.py 的 XfeiPdfOCRClient
配置文件: .key (JSON格式)
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

# ============ 引用官方OCR脚本 ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
OCR_SCRIPT_DIR = os.path.join(SKILL_DIR, 'ocr-skill', 'scripts')
sys.path.insert(0, OCR_SCRIPT_DIR)

try:
    from pdf_ocr import XfeiPdfOCRClient
except ImportError:
    print("错误: 无法导入官方OCR脚本")
    print(f"  路径: {OCR_SCRIPT_DIR}/pdf_ocr.py")
    print("  请确保 ocr-skill/scripts/pdf_ocr.py 存在")
    sys.exit(1)


# ============ 配置管理 ============

KEY_FILE = os.path.join(SKILL_DIR, '.key')


def load_config() -> dict:
    if not os.path.exists(KEY_FILE):
        return None
    try:
        with open(KEY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_config(config: dict):
    with open(KEY_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print(f"配置已保存到: {KEY_FILE}")


def get_config() -> dict:
    config = load_config()
    if config and all(k in config for k in ['APP_ID', 'API_SECRET']):
        return config
    return None


def prompt_config() -> dict:
    print("\n" + "=" * 60)
    print("需要配置科大讯飞OCR密钥")
    print("=" * 60)
    print("\n请提供以下信息（从 https://console.xfyun.cn/services/pdfOcr 获取）:\n")

    config = {}
    print("APP_ID: ", end="", flush=True)
    config['APP_ID'] = input().strip()
    print("API_SECRET: ", end="", flush=True)
    config['API_SECRET'] = input().strip()
    print("API_KEY: ", end="", flush=True)
    config['API_KEY'] = input().strip()

    if not config['APP_ID'] or not config['API_SECRET']:
        print("错误: APP_ID 和 API_SECRET 是必填项")
        return None

    save_config(config)
    return config


def update_config_interactive() -> dict:
    print("\n当前配置文件: " + KEY_FILE)
    old = load_config() or {}

    print(f"\n当前 APP_ID: {old.get('APP_ID', '未设置')}")
    print("输入新的 APP_ID (直接回车保持不变): ", end="", flush=True)
    v = input().strip()
    if v:
        old['APP_ID'] = v

    print(f"\n当前 API_SECRET: {old.get('API_SECRET', '未设置')[:10]}...")
    print("输入新的 API_SECRET (直接回车保持不变): ", end="", flush=True)
    v = input().strip()
    if v:
        old['API_SECRET'] = v

    print(f"\n当前 API_KEY: {old.get('API_KEY', '未设置')[:10]}...")
    print("输入新的 API_KEY (直接回车保持不变): ", end="", flush=True)
    v = input().strip()
    if v:
        old['API_KEY'] = v

    save_config(old)
    return old


# ============ 翻译部分 ============

CHINESE_RE = re.compile(r'[\u4e00-\u9fff]')
WT_TEXT_RE = re.compile(r'<w:t[^>]*>([^<]+)</w:t>')
WT_REPLACE_RE = re.compile(r'(<w:t[^>]*>)([^<]+)(</w:t>)')


def extract_chinese_texts(xml_content: str) -> list:
    texts = WT_TEXT_RE.findall(xml_content)
    return [t for t in texts if CHINESE_RE.search(t)]


def translate_xml_file(filepath: str, translations: dict) -> int:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    count = 0

    def replacer(m):
        nonlocal count
        open_tag, text, close_tag = m.groups()
        if text in translations:
            count += 1
            return f'{open_tag}{translations[text]}{close_tag}'
        return m.group(0)

    translated = WT_REPLACE_RE.sub(replacer, content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(translated)
    return count


def translate_word(cn_word: str, translations: dict, output_path: str, work_dir: str):
    print(f"\n{'=' * 60}")
    print("阶段2: 中文Word -> 英文Word")
    print(f"{'=' * 60}")

    extract_dir = os.path.join(work_dir, 'extracted')
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)

    with zipfile.ZipFile(cn_word, 'r') as z:
        z.extractall(extract_dir)

    total = 0
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith('.xml'):
                fp = os.path.join(root, f)
                cnt = translate_xml_file(fp, translations)
                if cnt > 0:
                    print(f"  {os.path.relpath(fp, extract_dir)}: {cnt}")
                    total += cnt

    doc_xml = os.path.join(extract_dir, 'word', 'document.xml')
    if os.path.exists(doc_xml):
        remaining = WT_TEXT_RE.findall(open(doc_xml, encoding='utf-8').read())
        remaining = [t for t in remaining if CHINESE_RE.search(t)]
        if remaining:
            print(f"\n警告: 还有 {len(remaining)} 条中文未翻译")

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(extract_dir):
            for f in files:
                fp = os.path.join(root, f)
                z.write(fp, os.path.relpath(fp, extract_dir))

    print(f"\n完成! 共翻译 {total} 处 -> {output_path}")


def extract_texts(docx_path: str, output_json: str) -> list:
    with zipfile.ZipFile(docx_path, 'r') as z:
        all_texts = set()
        for name in z.namelist():
            if name.endswith('.xml'):
                texts = extract_chinese_texts(z.read(name).decode('utf-8'))
                all_texts.update(texts)

    sorted_texts = sorted(list(all_texts))
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(sorted_texts, f, ensure_ascii=False, indent=2)

    print(f"提取 {len(sorted_texts)} 条中文 -> {output_json}")
    return sorted_texts


def create_batch_files(texts: list, work_dir: str, batch_size: int = 100):
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        fp = os.path.join(work_dir, f'translations_{i // batch_size + 1}.json')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump({t: "" for t in batch}, f, ensure_ascii=False, indent=2)
        print(f"  translations_{i // batch_size + 1}.json: {len(batch)} 条")


# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description='PDF OCR识别 + 翻译英文版')
    parser.add_argument('input', nargs='?', help='输入PDF文件')
    parser.add_argument('-o', '--output', help='输出英文Word')
    parser.add_argument('--work-dir', default='./temp_ocr_en')
    parser.add_argument('--skip-ocr', action='store_true', help='跳过OCR')
    parser.add_argument('--cn-word', help='已有中文Word')
    parser.add_argument('--translations', help='翻译JSON文件')
    parser.add_argument('--config', action='store_true', help='配置密钥')
    parser.add_argument('--batch-size', type=int, default=100)
    args = parser.parse_args()

    # 仅配置模式
    if args.config:
        config = get_config()
        if config:
            print(f"\n当前配置 ({KEY_FILE}):")
            print(f"  APP_ID: {config.get('APP_ID')}")
            print(f"  API_SECRET: {config.get('API_SECRET', '')[:10]}...")
            print(f"  API_KEY: {config.get('API_KEY', '')[:10]}...")
            print("\n是否更新? (y/n): ", end="", flush=True)
            if input().strip().lower() == 'y':
                update_config_interactive()
        else:
            prompt_config()
        return

    if not args.input:
        parser.print_help()
        return

    # 获取配置
    config = get_config()
    if not config:
        config = prompt_config()
        if not config:
            print("错误: 无法获取配置")
            sys.exit(1)

    work_dir = args.work_dir
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    output = args.output or args.input.replace('.pdf', '_en.docx')

    # ========== 阶段1: OCR（复用官方脚本） ==========
    if args.skip_ocr:
        cn_word = args.cn_word
        if not cn_word:
            print("错误: --skip-ocr 需要指定 --cn-word")
            sys.exit(1)
        print(f"跳过OCR，使用: {cn_word}")
    else:
        print(f"\n{'=' * 60}")
        print("阶段1: PDF OCR识别")
        print(f"{'=' * 60}")

        client = XfeiPdfOCRClient(config['APP_ID'], config['API_SECRET'])

        try:
            result = client.ocr(pdf_path=Path(args.input))
        except Exception as e:
            error_msg = str(e)
            print(f"\nOCR失败: {error_msg}")

            if any(code in error_msg for code in ['10313', '11200', '11201', '10001']):
                print("\n可能是密钥问题，需要更新配置")
                config = update_config_interactive()
                if config:
                    print("\n重试...")
                    try:
                        client = XfeiPdfOCRClient(config['APP_ID'], config['API_SECRET'])
                        result = client.ocr(pdf_path=Path(args.input))
                    except Exception as e2:
                        print(f"\n重试仍失败: {e2}")
                        print("请检查密钥是否正确，或联系科大讯飞客服")
                        sys.exit(1)
                else:
                    sys.exit(1)
            else:
                sys.exit(1)

        down_url = result['data'].get('downUrl')
        if not down_url:
            print("错误: 未获取到下载链接")
            sys.exit(1)

        cn_word = os.path.join(work_dir, 'cn_output.docx')
        import requests
        resp = requests.get(down_url, stream=True)
        with open(cn_word, 'wb') as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        print(f"下载: {cn_word}")

    # ========== 阶段2: 翻译 ==========
    if args.translations:
        with open(args.translations, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        translations = {k: v for k, v in translations.items() if v}
        translate_word(cn_word, translations, output, work_dir)
    else:
        print(f"\n{'=' * 60}")
        print("提取中文文本，创建分批翻译模板")
        print(f"{'=' * 60}")

        texts_file = os.path.join(work_dir, 'texts_to_translate.json')
        texts = extract_texts(cn_word, texts_file)

        print(f"\n创建翻译批次文件:")
        create_batch_files(texts, work_dir, args.batch_size)

        print(f"""
{'=' * 60}
请完成翻译后重新运行:
{'=' * 60}

1. 编辑 {work_dir}/translations_*.json 填写英文翻译
2. 运行:
   python scripts/ocr_translate.py {args.input} -o {output} \\
     --skip-ocr --cn-word {cn_word} \\
     --translations {work_dir}/all_translations.json
""")


if __name__ == '__main__':
    main()
