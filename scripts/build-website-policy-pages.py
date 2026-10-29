"""Copy the existing public policies and render four-language website documents."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'website'
BASE = 'http://anicanto.com/'
ISSUES = 'https://github.com/samuelkcc/AniCanto-Support/issues'
LOCALES = {'zh-HK': '.zh-HK', 'en': '', 'zh-Hans': '.zh-CN', 'ja': '.ja'}


def locale_for(suffix):
    return next(key for key, value in LOCALES.items() if value == (suffix or ''))


def relocate(text, support=False):
    text = text.replace('https://github.com/samuelkcc/AniCanto/issues', ISSUES)
    if support:
        text = text.replace('issues/new?title=', 'issues/new?template=technical-issue.yml&title=')
    text = re.sub(r'\((?:\.\./)?(?:docs/)?IPAD-PRIVACY-POLICY(\.zh-HK|\.zh-CN|\.ja)?\.md(?:#[^)]*)?\)',
                  lambda m: '(' + BASE + 'privacy.html?lang=' + locale_for(m[1]) + ')', text)
    text = re.sub(r'\((?:\.\./)?SUPPORT(\.zh-HK|\.zh-CN|\.ja)?\.md(?:#[^)]*)?\)',
                  lambda m: '(' + BASE + 'support.html?lang=' + locale_for(m[1]) + '#contact)', text)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if i < 6:
            lines[i] = re.sub(r'\((?:\.\./)?README(?:\.en|\.zh-HK|\.zh-CN|\.ja)?\.md\)', '(' + BASE + ')', line)
        elif support:
            lines[i] = re.sub(r'\((README(?:\.en|\.zh-HK|\.zh-CN|\.ja)?\.md)\)',
                              r'(https://github.com/samuelkcc/AniCanto/blob/main/\1)', line)
    return '\n'.join(lines) + '\n'


def inline(text):
    text = html.escape(text)
    text = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)


def render(text, locale):
    lines = text.splitlines()[6:]
    if locale == 'en':
        for i, line in enumerate(lines):
            if line == '## 繁體中文':
                lines = lines[:i]
                break
    output, paragraph, table = [], [], []
    list_type = None

    def flush_paragraph():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    def flush_table():
        if table:
            output.append('<div class="document-table"><table>')
            for i, cells in enumerate(table):
                tag = 'th' if i == 0 else 'td'
                output.append('<tr>' + ''.join(f'<{tag}>' + inline(c) + f'</{tag}>' for c in cells) + '</tr>')
            output.append('</table></div>')
            table.clear()

    def close_list():
        nonlocal list_type
        if list_type:
            output.append(f'</{list_type}>')
            list_type = None

    for line in lines + ['']:
        if line.startswith('|'):
            flush_paragraph()
            close_list()
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                table.append(cells)
            continue
        flush_table()
        match = re.match(r'^(#{1,6}) (.+)', line)
        item = re.match(r'^(?:- |\d+\. )(.+)', line)
        if not line:
            flush_paragraph()
            close_list()
        elif match:
            flush_paragraph()
            close_list()
            level = min(4, max(2, len(match[1])))
            output.append(f'<h{level}>' + inline(match[2]) + f'</h{level}>')
        elif item:
            flush_paragraph()
            kind = 'ul' if line.startswith('- ') else 'ol'
            if kind != list_type:
                close_list()
                output.append(f'<{kind}>')
                list_type = kind
            output.append('<li>' + inline(item[1]) + '</li>')
        else:
            close_list()
            paragraph.append(line)
    return '\n'.join(output)


def mobile_support(locale, suffix):
    copy = json.loads((ROOT / 'scripts/website-mobile-support-copy.json').read_text())[locale]
    languages = ' · '.join('[' + label + '](' + BASE + 'support.html?lang=' + code + ')' for code, label in
                         [('zh-HK', '繁體中文'), ('en', 'English'), ('zh-Hans', '简体中文'), ('ja', '日本語')])
    lines = ['# ' + copy['title'], '', languages, '', '[AniCanto](' + BASE + ') · [' + copy['privacy'] + '](' + BASE + 'privacy.html?lang=' + locale + ')', '',
             copy['intro'], '', '## ' + copy['contact'], '',
             '- [' + copy['ipad'] + '](' + ISSUES + '/new?template=technical-issue.yml&title=%5BiPad%5D%20)',
             '- [' + copy['iphone'] + '](' + ISSUES + '/new?template=technical-issue.yml&title=%5BiPhone%5D%20)',
             '- [' + copy['reports'] + '](' + ISSUES + ')', '', copy['notice'], '', '## ' + copy['details'], '']
    lines += [str(i) + '. ' + item for i, item in enumerate(copy['items'], 1)]
    lines += ['', '## ' + copy['help'], '']
    for paragraph in copy['paragraphs']:
        lines += [paragraph, '']
    lines += ['## ' + copy['privacy'], '', '[' + copy['privacy'] + '](' + BASE + 'privacy.html?lang=' + locale + ')', '',
              '## ' + copy['desktop'], '', '[' + copy['desktopLink'] + '](https://github.com/samuelkcc/AniCanto/blob/main/SUPPORT' + suffix + '.md)', '']
    return '\n'.join(lines)


def main():
    (SITE / 'docs').mkdir(exist_ok=True)
    for kind in ['privacy', 'support']:
        sections = []
        for locale, suffix in LOCALES.items():
            relative = Path('docs') / ('IPAD-PRIVACY-POLICY' + suffix + '.md') if kind == 'privacy' else Path('SUPPORT' + suffix + '.md')
            source = (ROOT / relative).read_text() if kind == 'privacy' else mobile_support(locale, suffix)
            relocated = relocate(source, support=kind == 'support')
            (SITE / relative).write_text(relocated)
            title = source.splitlines()[0].lstrip('# ')
            sections.append(f'<section id="lang-{locale}" lang="{locale}" data-document-language="{locale}" data-document-title="{html.escape(title)}"><h1>{html.escape(title)}</h1>{render(relocated, locale)}</section>')
        label = '私隱政策' if kind == 'privacy' else '技術支援'
        markup = '''<!doctype html>
<html lang="zh-HK"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#100c1c"><title>''' + label + ''' · AniCanto</title>
<link rel="icon" href="assets/favicon-shion-mic.png?v=20261028-shion-studio-mic-v2" type="image/png">
<link rel="stylesheet" href="styles.css?v=20261028-studio-v13-final"><script src="legal-pages.js?v=20261028-policy-v1" defer></script></head>
<body class="document-page"><header class="document-header"><a class="brand" href="./"><span class="brand-symbol" aria-hidden="true"><i class="brand-letter">a</i><span>♪</span></span>AniCanto</a><nav><a data-document-link="home" href="./">返回主頁</a><a data-document-link="privacy" href="privacy.html?lang=zh-HK">私隱政策</a><a data-document-link="support" href="support.html?lang=zh-HK">技術支援</a></nav></header>
<nav class="document-languages" aria-label="Language"><a data-document-choice="zh-HK" href="?lang=zh-HK#lang-zh-HK">繁體中文</a><a data-document-choice="en" href="?lang=en#lang-en">English</a><a data-document-choice="zh-Hans" href="?lang=zh-Hans#lang-zh-Hans">简体中文</a><a data-document-choice="ja" href="?lang=ja#lang-ja">日本語</a></nav>
<main id="contact" class="document-content">''' + '\n'.join(sections) + '''</main><footer class="document-footer"><a data-document-link="home" href="./">返回主頁</a><span>Copyright © 2026 SCKC · AniCanto</span></footer></body></html>'''
        (SITE / (kind + '.html')).write_text(markup)
    print(json.dumps({'pages': 2, 'languagesPerPage': 4, 'sourceDocuments': 8, 'policyBodyChanged': False}))


if __name__ == '__main__':
    main()
