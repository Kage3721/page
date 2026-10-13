import json
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parent
PDF = ROOT.parent / 'output/pdf/網頁設計_90題_手機複習版.pdf'
QA = ROOT.parent / 'tmp/pdfs/mobile'
manifest = json.loads((ROOT / 'mobile-pdf-layout.json').read_text(encoding='utf-8'))
images = sorted(QA.glob('page-*.png'))
assert len(images) == 94
with pdfplumber.open(PDF) as doc:
    for i, page in enumerate(doc.pages, 1):
        assert page.width == 390 and page.height >= 844
        for char in page.chars:
            assert 20 <= char['x0'] <= char['x1'] <= page.width - 19, (i, 'horizontal clipping', char['text'])
            assert 0 <= char['top'] <= char['bottom'] <= page.height, (i, 'vertical clipping', char['text'])
        assert '\ufffd' not in page.extract_text(), (i, 'missing character')
reader = PdfReader(PDF)
links = sum(len(page.get('/Annots', [])) for page in reader.pages)
assert links >= 184
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
tile_w, tile_h = 234, 507
for group in range((len(images) + 19) // 20):
    batch = images[group * 20:(group + 1) * 20]
    sheet = Image.new('RGB', (4 * tile_w, 5 * (tile_h + 30)), '#e4e9ec')
    draw = ImageDraw.Draw(sheet)
    for j, path in enumerate(batch):
        page = Image.open(path).convert('RGB')
        page.thumbnail((tile_w - 10, tile_h))
        x = (j % 4) * tile_w + 5
        y = (j // 4) * (tile_h + 30)
        sheet.paste(page, (x, y + 24))
        draw.text((x + 3, y + 3), f'PAGE {group * 20 + j + 1:02d}', fill='#333333', font=font)
    sheet.save(QA / f'contact-{group + 1}.jpg', quality=90)
longest = sorted(manifest, key=lambda q: q['content_bottom'])[:8]
print('All 94 pages rendered. Character bounds and missing-glyph checks passed.')
print(f'Navigation links: {links}.')
print('Densest pages: ' + ', '.join(f'{q["subject"]} Q{q["number"]} (page {q["page"]}, bottom {q["content_bottom"]:.1f})' for q in longest))
