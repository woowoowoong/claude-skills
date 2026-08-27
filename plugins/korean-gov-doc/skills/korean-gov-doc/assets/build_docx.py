#!/usr/bin/env python3
"""관공서 한글 문서 : Markdown -> Word(.docx) 빌드.

사용법
  1) 아래 경로 상수를 프로젝트에 맞게 고친다.
  2) ref.docx 를 만든다 :  cd refx && zip -Xrq ../ref.docx .
     (refx/ 는 assets/ 의 styles.xml, header1~2.xml, footer1~2.xml 및
      pandoc이 만든 docx에서 꺼낸 나머지 파트로 구성)
  3) python3 build_docx.py

하는 일
  - '---' 두 줄 연속 -> 페이지 나눔
  - pandoc 으로 docx 생성 (reference-doc 스타일 적용)
  - OOXML 후처리 : 표 머리행 음영, tblPr/pPr 요소 순서 정규화,
    갑지 표 격자선, 문단 간격(□ 앞 여백 등), 그림 삽입 영역,
    머리글/바닥글 연결, 표지 첫 페이지 머리글 제거(titlePg)
  - 스키마 위반 보정 (numbering nsid, settings.xml)

주의 : references/ooxml-pitfalls.md 를 읽고 나서 후처리를 추가할 것.
"""
import re, os, shutil, subprocess, zipfile, glob
from PIL import Image

W = '/root/work'                      # 작업 디렉터리
MD = f'{W}/문서.md'                    # 입력 Markdown
OUT = f'{W}/문서.docx'                 # 출력 docx

# 1) 전처리 --------------------------------------------------------------
src = open(MD, encoding='utf-8').read()
PB = '\n```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'
src = re.sub(r'\n-{3,}\n-{3,}\n', PB, src)      # 대구분선 -> 페이지 나눔
src = re.sub(r'\n-{3,}\n', '\n\n', src)          # 잔여 구분선 제거
open(f'{W}/build.md', 'w', encoding='utf-8').write(src)

# 2) pandoc --------------------------------------------------------------
subprocess.run(['pandoc', f'{W}/build.md', '-o', f'{W}/out.docx',
                '--reference-doc', f'{W}/ref.docx',
                '-f', 'markdown+pipe_tables+raw_attribute+hard_line_breaks'], check=True)

# 3) 후처리 --------------------------------------------------------------
ox = f'{W}/ox'
shutil.rmtree(ox, ignore_errors=True); os.makedirs(ox)
with zipfile.ZipFile(f'{W}/out.docx') as z:
    z.extractall(ox)

for f_ in ('header1.xml', 'footer1.xml', 'header2.xml', 'footer2.xml'):
    shutil.copy(f'{W}/refx/word/{f_}', f'{ox}/word/{f_}')

rp = f'{ox}/word/_rels/document.xml.rels'
r = open(rp, encoding='utf-8').read()
_add = ''
for tag, fn, rid in (('header', 'header1.xml', 'rIdHdr1'), ('footer', 'footer1.xml', 'rIdFtr1'),
                     ('header', 'header2.xml', 'rIdHdr2'), ('footer', 'footer2.xml', 'rIdFtr2')):
    if fn not in r:
        _add += ('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/'
                 '2006/relationships/%s" Target="%s"/>' % (rid, tag, fn))
if _add:
    r = r.replace('</Relationships>', _add + '</Relationships>')
    open(rp, 'w', encoding='utf-8').write(r)

# pandoc이 reference-doc의 rels를 가져오며 Id를 재부여하므로 실제 Id를 찾아 쓴다
def rel_id(target):
    m = re.search(r'<Relationship[^>]*Id="([^"]+)"[^>]*Target="%s"' % target, r)
    if m: return m.group(1)
    m = re.search(r'<Relationship[^>]*Target="%s"[^>]*Id="([^"]+)"' % target, r)
    return m.group(1) if m else None

HDR_ID = rel_id('header1.xml') or 'rIdHdr1'
FTR_ID = rel_id('footer1.xml') or 'rIdFtr1'
HDR_F_ID = rel_id('header2.xml') or 'rIdHdr2'
FTR_F_ID = rel_id('footer2.xml') or 'rIdFtr2'

cp = f'{ox}/[Content_Types].xml'
c = open(cp, encoding='utf-8').read()
_ov = ''
for fn, kind in (('header1.xml', 'header'), ('footer1.xml', 'footer'),
                 ('header2.xml', 'header'), ('footer2.xml', 'footer')):
    if '/word/%s' % fn not in c:
        _ov += ('<Override PartName="/word/%s" ContentType="application/vnd.openxmlformats-'
                'officedocument.wordprocessingml.%s+xml"/>' % (fn, kind))
if _ov:
    c = c.replace('</Types>', _ov + '</Types>')
    open(cp, 'w', encoding='utf-8').write(c)

p = f'{ox}/word/document.xml'
s = open(p, encoding='utf-8').read()

def fix_table(m):
    tbl = m.group(0)
    tr = re.search(r'<w:tr>.*?</w:tr>', tbl, re.S)
    if not tr:
        return tbl
    first = tr.group(0)
    new = first.replace('<w:tcPr />',
        '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/><w:vAlign w:val="center"/></w:tcPr>')
    new = re.sub(r'<w:r><w:t', '<w:r><w:rPr><w:b/></w:rPr><w:t', new)
    return tbl.replace(first, new, 1)

s = re.sub(r'<w:tbl>.*?</w:tbl>', fix_table, s, flags=re.S)



# tblPr 요소 순서 정규화: tblStyle, tblW, jc, tblLayout, tblLook
def fix_tblpr(m):
    inner = m.group(1)
    style = re.search(r'<w:tblStyle[^>]*/>', inner)
    w     = re.search(r'<w:tblW[^>]*/>', inner)
    jc    = re.search(r'<w:jc[^>]*/>', inner)
    bd    = re.search(r'<w:tblBorders>.*?</w:tblBorders>', inner, re.S)
    lay   = re.search(r'<w:tblLayout[^>]*/>', inner)
    mar   = re.search(r'<w:tblCellMar>.*?</w:tblCellMar>', inner, re.S)
    look  = re.search(r'<w:tblLook[^>]*/>', inner)
    parts = []
    if style: parts.append(style.group(0))
    if w:     parts.append(w.group(0))
    if jc:    parts.append(jc.group(0))
    if bd:    parts.append(bd.group(0))
    parts.append(lay.group(0) if lay else '<w:tblLayout w:type="autofit"/>')
    if mar:   parts.append(mar.group(0))
    if look:  parts.append(look.group(0))
    return '<w:tblPr>' + ''.join(parts) + '</w:tblPr>'

s = re.sub(r'<w:tblPr>(.*?)</w:tblPr>', fix_tblpr, s, flags=re.S)

# ── 갑지(첫 표) : 전체 격자선 + 행 높이 확보 (직인란) ──
GRID = ('<w:tblBorders>' +
        ''.join('<w:%s w:val="single" w:sz="6" w:space="0" w:color="404040"/>' % e
                for e in ('top', 'left', 'bottom', 'right')) +
        ''.join('<w:%s w:val="single" w:sz="4" w:space="0" w:color="808080"/>' % e
                for e in ('insideH', 'insideV')) + '</w:tblBorders>')

def gapji(m):
    tbl = m.group(0)
    tbl = tbl.replace('<w:tblLayout', GRID + '<w:tblLayout', 1)
    tbl = tbl.replace('<w:tcPr />', '<w:tcPr><w:vAlign w:val="center"/></w:tcPr>')
    def rowh(mm):
        tr = mm.group(0)
        if '<w:trPr>' in tr:
            return tr
        return tr.replace('<w:tr>',
            '<w:tr><w:trPr><w:trHeight w:hRule="atLeast" w:val="600"/></w:trPr>', 1)
    return re.sub(r'<w:tr>.*?</w:tr>', rowh, tbl, flags=re.S)

s = re.sub(r'<w:tbl>.*?</w:tbl>', gapji, s, count=1, flags=re.S)

# ── 문단 간격 : 개조식 □ 항목 앞 여백, 표 앞뒤 여백 (관공서 조판 관행) ──
BEFORE_BOX = 170     # □ 로 시작하는 중분류 앞 여백 (8.5pt)
AFTER_TBL  = 130     # 표 뒤 첫 문단 앞 여백
BEFORE_TBL = 90      # 표 앞 문단 뒤 여백

def _set_spacing(par, before=None, after=None):
    """pPr의 w:spacing 값을 조정. lineRule=exact(표지·요약 raw)는 건드리지 않음."""
    if 'w:lineRule="exact"' in par:
        return par
    if re.fullmatch(r'<w:p\b[^>]*/>', par.strip()):   # 자기닫힘 빈 문단
        return par
    attrs = ''
    if before is not None: attrs += ' w:before="%d"' % before
    if after is not None:  attrs += ' w:after="%d"' % after
    tag = '<w:spacing%s/>' % attrs

    m = re.search(r'<w:pPr>(.*?)</w:pPr>', par, re.S)
    if not m:
        if '<w:pPr />' in par:
            return par.replace('<w:pPr />', '<w:pPr>' + tag + '</w:pPr>', 1)
        return par.replace('<w:p>', '<w:p><w:pPr>' + tag + '</w:pPr>', 1)

    inner = m.group(1)
    ex = re.search(r'<w:spacing\b[^>]*/>', inner)
    if ex:
        t = ex.group(0)
        for k, v in (('before', before), ('after', after)):
            if v is None:
                continue
            if 'w:%s=' % k in t:
                t = re.sub(r'w:%s="\d+"' % k, 'w:%s="%d"' % (k, v), t)
            else:
                t = t.replace('<w:spacing', '<w:spacing w:%s="%d"' % (k, v), 1)
        new_inner = inner.replace(ex.group(0), t, 1)
    else:
        # CT_PPr 순서 : spacing 은 ind/jc/rPr 앞에 위치
        pos = len(inner)
        for nxt in ('<w:ind', '<w:jc', '<w:textAlignment', '<w:rPr'):
            i = inner.find(nxt)
            if i >= 0:
                pos = min(pos, i)
        new_inner = inner[:pos] + tag + inner[pos:]
    return par.replace(m.group(0), '<w:pPr>' + new_inner + '</w:pPr>', 1)

def _first_text(par):
    t = re.findall(r'<w:t[^>]*>(.*?)</w:t>', par, re.S)
    return ''.join(t).strip()

def space_body(m):
    """<w:body> 안에서 표 바깥 문단만 손본다."""
    body = m.group(1)
    parts = re.split(r'(<w:tbl>.*?</w:tbl>)', body, flags=re.S)
    for i, chunk in enumerate(parts):
        if chunk.startswith('<w:tbl>'):
            continue
        pars = re.split(r'(<w:p\b(?:[^>]*/>|.*?</w:p>))', chunk, flags=re.S)
        for j, par in enumerate(pars):
            if not par.startswith('<w:p'):
                continue
            txt = _first_text(par)
            if txt.startswith('□'):
                pars[j] = _set_spacing(par, before=BEFORE_BOX)
            elif txt.startswith('※'):
                pars[j] = _set_spacing(par, before=60)
        # 표 바로 뒤 첫 문단 / 표 바로 앞 마지막 문단
        idx = [j for j, x in enumerate(pars) if x.startswith('<w:p')]
        if idx and i > 0 and parts[i - 1].startswith('<w:tbl>'):
            pars[idx[0]] = _set_spacing(pars[idx[0]], before=AFTER_TBL)
        if idx and i + 1 < len(parts) and parts[i + 1].startswith('<w:tbl>'):
            pars[idx[-1]] = _set_spacing(pars[idx[-1]], after=BEFORE_TBL)
        parts[i] = ''.join(pars)
    return '<w:body>' + ''.join(parts) + '</w:body>'

s = re.sub(r'<w:body>(.*)</w:body>', space_body, s, flags=re.S)

# pandoc이 numPr 뒤에 pStyle을 두어 스키마 위반 -> pStyle을 앞으로
s = re.sub(r'<w:pPr>(<w:numPr>.*?</w:numPr>)(<w:pStyle[^>]*/>)',
           lambda m: '<w:pPr>' + m.group(2) + m.group(1), s, flags=re.S)

# ── 그림 자리 : 【그림 N】 문단을 실제 크기의 삽입 영역 박스 + 캡션으로 치환 ──
# 높이 단위 mm (1mm = 56.7 twips). 본문 1페이지 세로 유효폭 약 232mm
FIG_MM = {4: 66, 5: 72, 7: 72, 8: 62, 9: 66, 12: 82, 13: 66}
GRAY = '808080'

# figs/figNN.png 가 있으면 실제 이미지로 삽입
FIG_DIR = f'{W}/figs'
CONTENT_EMU = int(9864 / 1440 * 914400)   # 본문 폭 (A4 - 좌우여백)
_img_rels = []   # (relId, filename)

def fig_image(num, caption):
    matches = glob.glob(f'{FIG_DIR}/fig{num:02d}.*')
    if not matches:
        return None
    src = matches[0]
    ext = os.path.splitext(src)[1].lstrip('.').lower()
    fname = f'fig{num:02d}.{ext}'
    os.makedirs(f'{ox}/word/media', exist_ok=True)
    shutil.copy(src, f'{ox}/word/media/{fname}')
    with Image.open(src) as im:
        iw, ih = im.size
    cx = CONTENT_EMU
    cy = int(cx * ih / iw)
    rid = f'rIdFig{num}'
    _img_rels.append((rid, fname, ext))
    return (
      '<w:p><w:pPr><w:spacing w:before="80" w:after="40"/><w:jc w:val="center"/></w:pPr>'
      '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
      f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
      f'<wp:docPr id="{900+num}" name="figure{num}"/>'
      '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
      '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
      '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
      f'<pic:nvPicPr><pic:cNvPr id="{900+num}" name="{fname}"/><pic:cNvPicPr/></pic:nvPicPr>'
      '<pic:blipFill><a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      f'r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
      '<pic:spPr><a:xfrm><a:off x="0" y="0"/>'
      f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
      '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
      '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )

def fig_block(num, caption):
    mm = FIG_MM.get(num, 58)
    tw = int(mm * 56.7)
    box = (
      '<w:tbl><w:tblPr><w:tblW w:type="pct" w:w="5000"/><w:jc w:val="left"/>'
      '<w:tblBorders>'
      '<w:top w:val="dashed" w:sz="6" w:space="0" w:color="BFBFBF"/>'
      '<w:left w:val="dashed" w:sz="6" w:space="0" w:color="BFBFBF"/>'
      '<w:bottom w:val="dashed" w:sz="6" w:space="0" w:color="BFBFBF"/>'
      '<w:right w:val="dashed" w:sz="6" w:space="0" w:color="BFBFBF"/>'
      '</w:tblBorders><w:tblLayout w:type="autofit"/></w:tblPr>'
      '<w:tblGrid><w:gridCol w:w="9000"/></w:tblGrid>'
      '<w:tr><w:trPr><w:trHeight w:hRule="exact" w:val="%d"/><w:cantSplit/></w:trPr>'
      '<w:tc><w:tcPr><w:tcW w:type="pct" w:w="5000"/>'
      '<w:shd w:val="clear" w:color="auto" w:fill="FAFAFA"/>'
      '<w:vAlign w:val="center"/></w:tcPr>'
      '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:jc w:val="center"/></w:pPr>'
      '<w:r><w:rPr><w:rFonts w:ascii="맑은 고딕" w:eastAsia="맑은 고딕" w:hAnsi="맑은 고딕"/>'
      '<w:color w:val="%s"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr>'
      '<w:t xml:space="preserve">그림 %d 삽입 영역   (%dmm)</w:t></w:r></w:p>'
      '</w:tc></w:tr></w:tbl>' % (tw, GRAY, num, mm)
    )
    cap = (
      '<w:p><w:pPr><w:keepLines/><w:spacing w:before="60" w:after="160"/>'
      '<w:jc w:val="center"/></w:pPr>'
      '<w:r><w:rPr><w:rFonts w:ascii="맑은 고딕" w:eastAsia="맑은 고딕" w:hAnsi="맑은 고딕"/>'
      '<w:color w:val="595959"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr>'
      '<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % caption
    )
    # 박스 앞 여백 문단
    pre = ('<w:p><w:pPr><w:spacing w:before="0" w:after="60"/></w:pPr></w:p>')
    return pre + box + cap

def to_fig(m):
    para = m.group(0)
    texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', para, re.S)
    full = ''.join(texts)
    fm = re.match(r'【그림\s*(\d+)】\s*(.*)', full.strip(), re.S)
    if not fm:
        return para
    num = int(fm.group(1))
    cap = ('[그림 %d] ' % num) + fm.group(2).strip()
    real = fig_image(num, cap)
    if real:
        cap_p = ('<w:p><w:pPr><w:keepLines/><w:spacing w:before="20" w:after="110"/>'
                 '<w:jc w:val="center"/></w:pPr>'
                 '<w:r><w:rPr><w:rFonts w:ascii="맑은 고딕" w:eastAsia="맑은 고딕" w:hAnsi="맑은 고딕"/>'
                 '<w:color w:val="595959"/><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr>'
                 '<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % cap)
        return real + cap_p
    return fig_block(num, cap)

s = re.sub(r'<w:p>(?:(?!</w:p>).)*?【그림.*?</w:p>', to_fig, s, flags=re.S)

SECT = ('<w:sectPr><w:headerReference w:type="first" r:id="%s"/>' % HDR_F_ID +
        '<w:footerReference w:type="first" r:id="%s"/>' % FTR_F_ID +
        '<w:headerReference w:type="default" r:id="%s"/>' % HDR_ID +
        '<w:footerReference w:type="default" r:id="%s"/>' % FTR_ID +
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1304" w:right="1021" w:bottom="1247" w:left="1021" '
        'w:header="680" w:footer="600" w:gutter="0"/>'
        '<w:cols w:space="720"/><w:titlePg/>'
        '<w:docGrid w:linePitch="360"/></w:sectPr>')
if '<w:sectPr />' in s:
    s = s.replace('<w:sectPr />', SECT)
elif re.search(r'<w:sectPr[ >].*?</w:sectPr>', s, re.S):
    s = re.sub(r'<w:sectPr[ >].*?</w:sectPr>', SECT, s, flags=re.S)
else:
    s = s.replace('</w:body>', SECT + '</w:body>')

open(p, 'w', encoding='utf-8').write(s)

# 그림 이미지 관계 및 콘텐츠 타입 등록
if _img_rels:
    r2 = open(rp, encoding='utf-8').read()
    add = ''.join(
        '<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/%s"/>' % (rid, fn)
        for rid, fn, ext in _img_rels)
    r2 = r2.replace('</Relationships>', add + '</Relationships>')
    open(rp, 'w', encoding='utf-8').write(r2)

    c2 = open(cp, encoding='utf-8').read()
    for ext in {e for _, _, e in _img_rels}:
        mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}.get(ext, 'image/png')
        if 'Extension="%s"' % ext not in c2:
            c2 = c2.replace('<Types', '<Types', 1)
            c2 = c2.replace('</Types>', '<Default Extension="%s" ContentType="%s"/></Types>' % (ext, mime))
    open(cp, 'w', encoding='utf-8').write(c2)

# pandoc 자체 결함 보정: numbering.xml nsid 길이(8자리), settings.xml zoom 위치
np_ = f'{ox}/word/numbering.xml'
if os.path.exists(np_):
    n = open(np_, encoding='utf-8').read()
    n = re.sub(r'(<w:nsid w:val=")([0-9A-Fa-f]{1,7})(")',
               lambda m: m.group(1) + m.group(2).rjust(8, '0') + m.group(3), n)
    open(np_, 'w', encoding='utf-8').write(n)

# settings.xml: pandoc이 요소 순서를 어겨 스키마 오류가 나므로 최소 유효본으로 교체
SETTINGS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
  '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
  '<w:zoom w:percent="100"/>'
  '<w:defaultTabStop w:val="720"/>'
  '<w:characterSpacingControl w:val="compressPunctuation"/>'
  '<w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'
  '<w:endnotePr><w:endnote w:id="-1"/><w:endnote w:id="0"/></w:endnotePr>'
  '<w:compat><w:compatSetting w:name="compatibilityMode" '
  'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
  '<w:themeFontLang w:val="en-US" w:eastAsia="ko-KR"/>'
  '<w:decimalSymbol w:val="."/><w:listSeparator w:val=","/>'
  '</w:settings>')
open(f'{ox}/word/settings.xml', 'w', encoding='utf-8').write(SETTINGS)

# 4) 재압축 ---------------------------------------------------------------
if os.path.exists(OUT):
    os.remove(OUT)
subprocess.run(['zip', '-Xrq', OUT, '.'], cwd=ox, check=True)
print('built:', OUT)
