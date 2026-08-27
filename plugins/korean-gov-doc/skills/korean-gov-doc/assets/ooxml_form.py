#!/usr/bin/env python3
"""공고문 양식표(세로병합 포함)를 raw OOXML로 생성하는 헬퍼.

pandoc 파이프 표로는 vMerge(세로병합)를 만들 수 없다. 갑지·요약표처럼
라벨 셀이 여러 행을 묶는 양식은 이 헬퍼로 OOXML을 만들어
Markdown 안에 ```{=openxml} 블록으로 주입한다.

사용 예
    BLOCK = tbl(G1, rowsA) + gap(120) + tbl(G2, rowsB)
    md = md[:start] + '```{=openxml}\\n' + BLOCK + '\\n```\\n' + md[end:]

주의
  - 표 전체 폭 9864 twips = A4 좌우 여백 1021 기준 본문 폭.
    여백을 바꾸면 이 값도 바꾼다.
  - 고정 레이아웃에는 para(...) 대신 gap(twips)/exact 줄높이를 쓴다.
    Word와 LibreOffice의 줄높이 차이를 없애기 위함.
"""

FONT = ('<w:rFonts w:ascii="맑은 고딕" w:eastAsia="맑은 고딕" w:hAnsi="맑은 고딕" '
        'w:cs="맑은 고딕"/>')

# 바깥 0.75pt 진회색 / 안쪽 0.5pt 회색
BORDERS = (''.join('<w:%s w:val="single" w:sz="6" w:space="0" w:color="404040"/>' % e
                   for e in ('top', 'left', 'bottom', 'right')) +
           ''.join('<w:%s w:val="single" w:sz="4" w:space="0" w:color="808080"/>' % e
                   for e in ('insideH', 'insideV')))

LBL = 'D9D9D9'      # 라벨 셀 음영
SUBLBL = 'F2F2F2'   # 보조 라벨 셀 음영
CONTENT_W = 9864    # 본문 폭 (twips)


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def parse_bold(text):
    """**굵게** 마크업을 (조각, 굵기) 목록으로 분해."""
    parts, cur, i = [], '', 0
    while i < len(text):
        if text.startswith('**', i):
            j = text.find('**', i + 2)
            if j > 0:
                if cur:
                    parts.append((cur, False)); cur = ''
                parts.append((text[i + 2:j], True)); i = j + 2; continue
        cur += text[i]; i += 1
    if cur:
        parts.append((cur, False))
    return parts or [(text, False)]


def rpr(sz=18, b=False, color=None):
    out = '<w:rPr>' + FONT + ('<w:b/>' if b else '')
    if color:
        out += '<w:color w:val="%s"/>' % color
    return out + '<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>' % (sz, sz)


def para(text, sz=18, b=False, jc='left', ind=0, color=None,
         before=4, after=4, line=228, exact=False):
    """문단. sz 는 half-point (18 = 9pt).

    exact=True 면 line 을 고정 높이로 쓴다 (Word/LO 편차 제거용).
    """
    rule = 'exact' if exact else 'auto'
    ppr = ('<w:pPr><w:spacing w:before="%d" w:after="%d" w:line="%d" '
           'w:lineRule="%s"/>' % (before, after, line, rule))
    if ind:
        ppr += '<w:ind w:left="%d" w:hanging="%d"/>' % (ind, ind)
    ppr += '<w:jc w:val="%s"/></w:pPr>' % jc
    if text == '':
        return '<w:p>' + ppr + '</w:p>'
    runs = ''
    for seg, bold in parse_bold(text):
        runs += ('<w:r>' + rpr(sz, bold or b, color) +
                 '<w:t xml:space="preserve">' + esc(seg) + '</w:t></w:r>')
    return '<w:p>' + ppr + runs + '</w:p>'


def gap(twips):
    """높이를 고정한 빈 줄. 표지 등 고정 레이아웃에 쓴다."""
    return ('<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="%d" '
            'w:lineRule="exact"/><w:rPr><w:sz w:val="2"/></w:rPr></w:pPr></w:p>' % twips)


def bullets(items, sz=18, mark='○ ', ind=170):
    return ''.join(para(mark + t, sz=sz, ind=ind) for t in items)


def tc(width, paras, span=1, vmerge=None, shade=None, valign='center'):
    """셀. vmerge = 'restart'(병합 시작) | 'cont'(병합 계속, 내용은 '')."""
    pr = '<w:tcPr><w:tcW w:w="%d" w:type="dxa"/>' % width
    if span > 1:
        pr += '<w:gridSpan w:val="%d"/>' % span
    if vmerge == 'restart':
        pr += '<w:vMerge w:val="restart"/>'
    elif vmerge == 'cont':
        pr += '<w:vMerge/>'
    if shade:
        pr += '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade
    pr += '<w:vAlign w:val="%s"/></w:tcPr>' % valign
    return '<w:tc>' + pr + (paras or para('')) + '</w:tc>'


def tr(cells, height=None):
    pr = ''
    if height:
        pr = '<w:trPr><w:trHeight w:hRule="atLeast" w:val="%d"/></w:trPr>' % height
    return '<w:tr>' + pr + ''.join(cells) + '</w:tr>'


def tbl(grid, rows, width=CONTENT_W):
    """grid = 열 폭 목록(twips). 합이 width 와 같아야 한다."""
    return ('<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/>' % width +
            '<w:jc w:val="left"/><w:tblBorders>' + BORDERS + '</w:tblBorders>'
            '<w:tblLayout w:type="fixed"/>'
            '<w:tblCellMar>'
            '<w:top w:w="40" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
            '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="100" w:type="dxa"/>'
            '</w:tblCellMar></w:tblPr>'
            '<w:tblGrid>' + ''.join('<w:gridCol w:w="%d"/>' % g for g in grid) +
            '</w:tblGrid>' + ''.join(rows) + '</w:tbl>')


# ── 예 : 공고문 요약표 (라벨 세로병합) ────────────────────────────────────
if __name__ == '__main__':
    G = [1420, 1700, 6744]          # 라벨 / 보조라벨 / 내용
    rows = [
        tr([tc(G[0] + G[1], para('참가 주제명', b=True, jc='center'),
               span=2, shade=LBL),
            tc(G[2], para('**주제명** — 부제'))], height=380),
        tr([tc(G[0], para('기술요약', b=True, jc='center'),
               vmerge='restart', shade=LBL),
            tc(G[1], para('기술 개요', jc='center'), shade=SUBLBL),
            tc(G[2], bullets(['첫째 항목', '둘째 항목']))]),
        tr([tc(G[0], '', vmerge='cont', shade=LBL),
            tc(G[1], para('제안 특징점', jc='center'), shade=SUBLBL),
            tc(G[2], bullets(['특징 하나', '특징 둘']))]),
    ]
    print(tbl(G, rows)[:400], '...')
