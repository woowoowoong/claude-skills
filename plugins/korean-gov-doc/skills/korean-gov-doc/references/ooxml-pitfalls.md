# pandoc → docx 후처리 함정

pandoc이 만든 OOXML은 Word에서 열리기는 하지만 ISO-29500 스키마를 자주 위반한다. 검증기를 돌리면 잡히고, 일부는 Word가 "복구가 필요합니다" 경고를 띄운다. 아래는 실제로 부딪힌 것들이다.

## 요소 순서

XSD가 sequence로 정의한 요소들이라 **순서를 지키지 않으면 무조건 오류**다.

### `<w:pPr>` (CT_PPr)

```
pStyle → keepNext → keepLines → pageBreakBefore → framePr → widowControl
→ numPr → suppressLineNumbers → pBdr → shd → tabs → suppressAutoHyphens
→ kinsoku → wordWrap → overflowPunct → topLinePunct → autoSpaceDE → autoSpaceDN
→ bidi → adjustRightInd → snapToGrid → spacing → ind → jc → textDirection
→ textAlignment → textboxTightWrap → outlineLvl → divId → cnfStyle
→ rPr → sectPr → pPrChange
```

자주 걸리는 것:

- pandoc이 `numPr`을 `pStyle` **앞에** 두는 경우가 있다 → 순서를 바꿔야 한다.
- `spacing`을 추가할 때는 `ind` / `jc` / `rPr` **앞**에 넣어야 한다.
- 제목 스타일에서 `pBdr`은 `jc` 앞, `outlineLvl`은 뒤.

`spacing`을 넣을 때 **문단 전체 문자열에서 `<w:rPr`을 찾으면 안 된다.** 첫 번째 run 안의 `<w:rPr>`이 잡혀서 `<w:r>` 내부에 `<w:spacing>`이 꽂힌다(=`w:r`은 `spacing` 자식을 허용하지 않음). 반드시 `<w:pPr> … </w:pPr>` 구간을 먼저 잘라내고 그 안에서만 위치를 찾는다.

자기닫힘 문단 `<w:p />`에 `<w:pPr>`을 문자열로 붙이면 pPr이 문단 밖으로 나가서 "pPr not expected, expected sectPr" 오류가 난다. 자기닫힘 문단은 건너뛰거나 정식으로 열고 닫는다.

### `<w:tblPr>` (CT_TblPrBase)

```
tblStyle → tblpPr → tblOverlap → bidiVisual → tblStyleRowBandSize
→ tblStyleColBandSize → tblW → jc → tblCellSpacing → tblInd → tblBorders
→ shd → tblLayout → tblCellMar → tblLook
```

`tblBorders`는 `jc` 뒤 `tblLayout` 앞, `tblCellMar`는 `tblLayout` 뒤 `tblLook` 앞.

**tblPr을 정규화하는 후처리를 쓸 때 `tblBorders`와 `tblCellMar`를 보존해야 한다.** 이 둘을 버리면, 표 자체에 테두리를 직접 지정한 raw OOXML 표(갑지·요약표)에서 선이 통째로 사라진다. 본문 표는 스타일에서 테두리를 받으므로 증상이 안 보여서 원인을 찾기 어렵다.

### `<w:sectPr>` (CT_SectPr)

```
headerReference* / footerReference* → footnotePr → endnotePr → type
→ pgSz → pgMar → paperSrc → pgBorders → lnNumType → pgNumType → cols
→ formProt → vAlign → noEndnote → titlePg → textDirection → bidi
→ rtlGutter → docGrid → printerSettings → sectPrChange
```

`<w:titlePg/>`는 `cols` 뒤, `docGrid` 앞. 앞쪽에 두면 오류.

## 그 밖의 보정

| 증상 | 원인 | 조치 |
|---|---|---|
| 머리글·바닥글이 안 나옴 | pandoc이 reference-doc의 relationship Id를 재부여함 (`rIdHdr1` → `rId9`) | `document.xml.rels`에서 Target으로 실제 Id를 역조회해서 쓴다 |
| `numbering.xml` 스키마 오류 | `w:nsid` 값이 8자리 hex가 아님 | 앞을 0으로 채워 8자리로 맞춘다 |
| `settings.xml` 스키마 오류 | pandoc이 요소 순서를 어김 | 최소 유효본으로 통째 교체 |
| `<w:sectPr />` 치환 실패 | 자기닫힘 형태라 `<w:sectPr>…</w:sectPr>` 정규식에 안 걸림 | 자기닫힘 분기를 따로 둔다 |
| 표 셀 안 `<br>`이 사라지고 글자가 붙음 | pandoc이 표 셀 내 줄바꿈을 버림 | `<br>` 대신 `  ·  ` 같은 구분자를 쓴다 |
| 그림 삽입 영역이 잘림 | 캔버스 높이 부족 | 생성 시 캔버스를 넉넉히 잡고 크롭한다 |

## 검증

```bash
python3 <docx-skill>/scripts/office/validate.py out.docx --original ref.docx
```

`--original`에 reference-doc을 주면, 원본이 이미 갖고 있던 무해한 경고를 제외하고 **새로 생긴 오류만** 보고한다. 이걸 안 주면 styles.xml의 기존 경고 4건이 매번 실패로 잡힌다.

오류 위치를 특정하려면 lxml로 직접 검증해서 `error_log`의 `path`를 본다. 줄/열 번호는 한 줄짜리 XML이라 쓸모가 없다.

```python
from lxml import etree
import zipfile
sch = etree.XMLSchema(etree.parse('.../schemas/ISO-IEC29500-4_2016/wml.xsd'))
doc = etree.fromstring(zipfile.ZipFile('out.docx').read('word/document.xml'))
sch.validate(doc)
for e in sch.error_log:
    print(e.path, '|', e.message[:120])
```
