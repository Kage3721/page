import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
OUTPUT = OUT / '網頁設計_90題_手機複習版.pdf'
WIDTH = 390
BASE_HEIGHT = 844
MARGIN = 24
INK = colors.HexColor('#20272B')
MUTED = colors.HexColor('#657178')
LINE = colors.HexColor('#DEE5E8')
ACCENTS = {
    'HTML': colors.HexColor('#B84E37'),
    'CSS': colors.HexColor('#087E88'),
    'Bootstrap5': colors.HexColor('#356B46'),
}
FONTS = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('ZH', str(FONTS / 'msjh.ttc'), subfontIndex=0))
pdfmetrics.registerFont(TTFont('ZHB', str(FONTS / 'msjhbd.ttc'), subfontIndex=0))
pdfmetrics.registerFont(TTFont('EN', str(FONTS / 'arial.ttf')))
pdfmetrics.registerFont(TTFont('ENB', str(FONTS / 'arialbd.ttf')))
pdfmetrics.registerFont(TTFont('Code', str(FONTS / 'consola.ttf')))


def para(text, font='ZH', size=13, leading=None, color=INK, width=WIDTH - 2 * MARGIN):
    style = ParagraphStyle(
        'body', fontName=font, fontSize=size, leading=leading or size * 1.46,
        textColor=color, wordWrap='CJK' if font in ('ZH', 'ZHB', 'Code') else None, splitLongWords=1,
        allowWidows=0, allowOrphans=0,
    )
    markup = escape(text).replace('\n', '<br/>')
    p = Paragraph(markup, style)
    # Leave room for CJK punctuation that ReportLab hangs beyond the line width.
    _, height = p.wrap(width - 16, 10000)
    return p, height


def code_font(text):
    return 'Code' if any(t in text for t in ['<', '{', '}', ':', '#', '="', '/*']) or text.startswith('.') else 'EN'


def load_questions():
    translations = json.loads((ROOT / 'quiz-translations.json').read_text(encoding='utf-8'))
    translations['Bootstrap5'] = json.loads((ROOT / 'bootstrap5-translations.json').read_text(encoding='utf-8'))
    definitions = [('HTML', 'HTML', 40), ('CSS', 'CSS', 25), ('Bootstrap5', 'Bootstrap 5', 25)]
    subjects = []
    for key, title, count in definitions:
        source = (ROOT / f'{key}_Quiz_中文翻譯解析.txt').read_text(encoding='utf-8')
        chunks = re.findall(r'(?ms)^【英文原文】\n(.*?)^正確答案（英文原文）：([^\n]*)', source)
        assert len(chunks) == count
        questions = []
        for i, ((english, answer), row) in enumerate(zip(chunks, translations[key]), start=1):
            lines = english.strip().splitlines()
            assert lines[0] == f'Question {i}:'
            first_option = next(j for j, line in enumerate(lines) if re.search(r'\s+(Your answer|Correct answer)\s*$', line))
            stem = '\n'.join(lines[1:first_option]).strip()
            options = [re.sub(r'\s+(Your answer|Correct answer)\s*$', '', line).rstrip()
                       for line in lines[first_option:] if line.strip()]
            assert len(options) == len(row['optionsZh'])
            assert answer == row['answer'] and answer in options
            questions.append(dict(row, number=i, stem=stem, options=options, correct=options.index(answer)))
        subjects.append({'key': key, 'title': title, 'questions': questions})
    return subjects


def question_items(subject, q):
    accent = ACCENTS[subject['key']]
    items = []

    def add(text, font='ZH', size=13, gap=5, color=INK, indent=0, leading=None, kind='text'):
        p, height = para(text, font, size, leading, color, WIDTH - 2 * MARGIN - indent)
        items.append({'paragraph': p, 'height': height, 'gap': gap, 'indent': indent, 'kind': kind})

    add('英文題目', 'ZHB', 11, gap=6, color=accent)
    add(q['stem'], 'ENB', 16, gap=12, leading=22)
    for i, option in enumerate(q['options']):
        font = code_font(option)
        add(f'{chr(65 + i)}.  {option}', font, 13.5 if font == 'Code' else 14.5, gap=7, leading=20)
    add('正確答案 / ANSWER', 'ZHB', 10.5, gap=5, color=accent, kind='answer_label')
    add(f'{chr(65 + q["correct"])}.  {q["answer"]}', code_font(q['answer']), 14, gap=14, indent=10, leading=21, kind='answer')
    add('中文翻譯', 'ZHB', 11, gap=6, color=accent, kind='section')
    chinese_stem = q['zh']
    if subject['key'] == 'HTML' and q['number'] == 31:
        chinese_stem = chinese_stem.replace(' 有什麼用途', '\n有什麼用途')
    add(chinese_stem, 'ZHB', 15, gap=8, leading=22)
    for i, option in enumerate(q['optionsZh']):
        add(f'{chr(65 + i)}.  {option}', 'ZH', 14, gap=5, leading=20)
    add('解析', 'ZHB', 11, gap=6, color=accent, kind='section')
    add(q['explanation'], 'ZH', 14.5, gap=7, leading=21.5)
    if q.get('reference'):
        add('補充資料：官方文件', 'ZH', 10.5, color=MUTED, kind='reference')
        items[-1]['url'] = q['reference']
    return items


subjects = load_questions()
c = Canvas(str(OUTPUT), pagesize=(WIDTH, BASE_HEIGHT), pageCompression=1)
c.setTitle('網頁設計期中複習 | HTML・CSS・Bootstrap 5 | 手機版')
c.setAuthor('中英對照複習資料')
c.setSubject('90 題英文原文、選項、正確答案與繁體中文翻譯解析')
c.setViewerPreference('DisplayDocTitle', 'true')
page_number = 0
manifest = []


def new_page(height=BASE_HEIGHT):
    global page_number
    page_number += 1
    c.setPageSize((WIDTH, height))
    c.setFillColor(colors.white)
    c.rect(0, 0, WIDTH, height, fill=1, stroke=0)
    return height


def text_at(text, y, font='ZH', size=13, color=INK, x=MARGIN, width=WIDTH - 2 * MARGIN):
    p, h = para(text, font, size, color=color, width=width)
    p.drawOn(c, x, y - h)
    return y - h


def footer(height, section='CONTENTS', back='contents'):
    c.setStrokeColor(LINE)
    c.line(MARGIN, 42, WIDTH - MARGIN, 42)
    c.setFont('ZH', 10)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, 24, '返回目錄')
    c.linkRect('', back, (MARGIN - 3, 16, MARGIN + 72, 38), relative=0, thickness=0)
    c.setFont('EN', 9.5)
    c.drawRightString(WIDTH - MARGIN, 24, f'{section}  /  {page_number:03d}')


# A compact contents page is the first screen on a phone.
h = new_page()
c.bookmarkPage('contents')
c.addOutlineEntry('目錄', 'contents', 0, closed=False)
c.setFillColor(ACCENTS['CSS'])
c.rect(0, h - 8, WIDTH, 8, fill=1, stroke=0)
y = text_at('MIDTERM REVIEW', h - 42, 'ENB', 11, ACCENTS['CSS'])
y = text_at('網頁設計\n中英題庫', y - 16, 'ZHB', 32)
y = text_at('HTML / CSS / Bootstrap 5', y - 12, 'EN', 14, MUTED)
y = text_at('90 題  ·  英文原題與選項  ·  中文翻譯與解析', y - 16, size=12.2, color=MUTED)
y -= 27
for subject in subjects:
    accent = ACCENTS[subject['key']]
    c.setFillColor(accent)
    c.rect(MARGIN, y - 71, 4, 71, fill=1, stroke=0)
    c.setFont('ENB', 23)
    c.setFillColor(INK)
    c.drawString(MARGIN + 17, y - 27, subject['title'])
    c.setFont('ZH', 12)
    c.setFillColor(MUTED)
    c.drawString(MARGIN + 17, y - 52, f'{len(subject["questions"])} 題  /  題號目錄')
    c.linkRect('', f'index-{subject["key"]}', (MARGIN, y - 74, WIDTH - MARGIN, y + 2), thickness=0)
    c.setStrokeColor(LINE)
    c.line(MARGIN, y - 86, WIDTH - MARGIN, y - 86)
    y -= 105
y = text_at('閱讀順序', y - 4, 'ZHB', 12, ACCENTS['CSS'])
y = text_at('每題先看英文題目與選項，再對照答案、中文翻譯和解析。可點科目與題號跳轉，也可使用 PDF 書籤。', y - 7, size=12.4)
y = text_at('英文文字、選項順序與正確答案沿用你提供的三份題庫；換行僅為排版。原始作答紀錄與成績不納入複習頁，避免混淆。', y - 15, size=11.2, color=MUTED)
assert y > 65
footer(h)
c.showPage()

for subject in subjects:
    key = subject['key']
    accent = ACCENTS[key]
    h = new_page()
    c.bookmarkPage(f'index-{key}')
    c.addOutlineEntry(f'{subject["title"]} - {len(subject["questions"])} 題', f'index-{key}', 0, closed=True)
    c.setFillColor(accent)
    c.rect(0, h - 8, WIDTH, 8, fill=1, stroke=0)
    y = text_at(subject['title'], h - 40, 'ENB', 27)
    y = text_at('題號目錄', y - 10, 'ZHB', 16, accent)
    y = text_at('點選題號即可跳到該題', y - 8, size=12, color=MUTED)
    y -= 24
    columns = 5
    cell_w = (WIDTH - 2 * MARGIN) / columns
    cell_h = 48
    for i, q in enumerate(subject['questions']):
        col, row = i % columns, i // columns
        x = MARGIN + col * cell_w
        top = y - row * cell_h
        c.setStrokeColor(LINE)
        c.line(x + 5, top - cell_h + 6, x + cell_w - 5, top - cell_h + 6)
        c.setFont('ENB', 17)
        c.setFillColor(accent)
        c.drawCentredString(x + cell_w / 2, top - 25, f'{q["number"]:02d}')
        c.linkRect('', f'q-{key}-{q["number"]}', (x, top - cell_h, x + cell_w, top), thickness=0)
    y -= ((len(subject['questions']) + columns - 1) // columns) * cell_h + 28
    text_at('英文原題 → 正確答案 → 中文對照 → 解析', y, size=11.2, color=MUTED)
    footer(h, subject['title'])
    c.showPage()

    for q in subject['questions']:
        items = question_items(subject, q)
        needed = sum(item['height'] + item['gap'] for item in items)
        h = new_page(max(BASE_HEIGHT, needed + 151))
        dest = f'q-{key}-{q["number"]}'
        c.bookmarkPage(dest)
        c.addOutlineEntry(f'{q["number"]:02d}  {q["zh"]}', dest, 1, closed=True)
        c.setFillColor(accent)
        c.rect(0, h - 5, WIDTH, 5, fill=1, stroke=0)
        c.setFont('ENB', 15)
        c.setFillColor(INK)
        c.drawString(MARGIN, h - 34, subject['title'])
        c.setFont('ENB', 12)
        c.setFillColor(accent)
        c.drawRightString(WIDTH - MARGIN, h - 34, f'{q["number"]:02d} / {len(subject["questions"])}')
        c.setStrokeColor(LINE)
        c.line(MARGIN, h - 49, WIDTH - MARGIN, h - 49)
        y = h - 68
        for item in items:
            p, ph = item['paragraph'], item['height']
            if item['kind'] == 'section':
                c.setStrokeColor(LINE)
                c.line(MARGIN, y + 4, WIDTH - MARGIN, y + 4)
                y -= 9
            if item['kind'] == 'answer':
                c.setFillColor(colors.HexColor('#EFF5F4'))
                c.rect(MARGIN, y - ph - 5, WIDTH - 2 * MARGIN, ph + 10, fill=1, stroke=0)
                c.setFillColor(accent)
                c.rect(MARGIN, y - ph - 5, 3, ph + 10, fill=1, stroke=0)
            p.drawOn(c, MARGIN + item['indent'], y - ph)
            if item.get('url'):
                c.linkURL(item['url'], (MARGIN, y - ph, WIDTH - MARGIN, y), relative=0, thickness=0)
            y -= ph + item['gap']
        assert y > 56, (key, q['number'], y)
        footer(h, f'{subject["title"]} Q{q["number"]:02d}', f'index-{key}')
        manifest.append({'subject': key, 'number': q['number'], 'page': page_number,
                         'height': h, 'content_bottom': y, 'stem': q['stem'],
                         'options': q['options'], 'answer': q['answer'],
                         'zh': q['zh'], 'explanation': q['explanation']})
        c.showPage()

c.save()

# Validate the rendered text against the provided originals, allowing line wraps only.
reader = PdfReader(OUTPUT)
assert len(reader.pages) == 94
normalize = lambda value: re.sub(r'\s+', '', value)
for q in manifest:
    page = reader.pages[q['page'] - 1]
    text = normalize(page.extract_text())
    for original in [q['stem'], *q['options'], q['answer'], q['zh'], q['explanation']]:
        assert normalize(original) in text, (q['subject'], q['number'], original)
    assert page.get('/Annots'), 'Missing navigation link'
assert len(manifest) == 90
assert len(reader.outline) >= 4
(ROOT / 'mobile-pdf-layout.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Created: {OUTPUT}')
print(f'Validated: {len(reader.pages)} pages; 90 questions; every English stem, option and answer preserved.')
print(f'Page heights: {min(q["height"] for q in manifest):.0f}-{max(q["height"] for q in manifest):.0f} pt')
print(f'File size: {OUTPUT.stat().st_size / 1024 / 1024:.2f} MB')
