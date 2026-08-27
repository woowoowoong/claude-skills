# csw-skills

창소프트아이앤아이 사내 공용 Claude 스킬 모음입니다. Claude Code / Cowork에서 **플러그인 마켓플레이스**로 설치해 씁니다.

## 설치

```
/plugin marketplace add <GitHub계정>/claude-skills
/plugin install korean-gov-doc@csw-skills
```

사내 GitLab이나 로컬 경로도 됩니다.

```
/plugin marketplace add https://gitlab.example.com/team/claude-skills.git
/plugin marketplace add ./claude-skills
```

## 갱신

```
/plugin marketplace update csw-skills
/plugin update korean-gov-doc
```

기본적으로 하루 한 번 자동으로도 받아옵니다. `plugin.json`의 `version`을 올린 커밋만 배포되므로, **내용을 고쳤으면 버전을 함께 올려야** 사용자에게 전달됩니다.

## 수록 스킬

| 플러그인 | 스킬 | 내용 |
|---|---|---|
| `korean-gov-doc` | `korean-gov-doc` | 관공서·공공기관 제출용 한글 문서 작성·조판. 개조식 본문 규칙, 조판 수치, 공고문 양식(갑지·요약표) 재현, pandoc → OOXML 빌드 파이프라인 |

## 스킬 추가하는 법

1. `plugins/<플러그인명>/` 생성
2. `.claude-plugin/plugin.json` 작성 (name·version·description 필수)
3. `skills/<스킬명>/SKILL.md` 작성 — frontmatter의 `name`은 디렉터리명과 같게, `description`에는 **언제 이 스킬을 쓰는지**를 구체적으로 적는다. 이 문장으로 스킬이 호출될지가 정해지므로 가장 중요하다
4. 루트 `.claude-plugin/marketplace.json`의 `plugins` 배열에 항목 추가
5. 커밋 · 푸시

분량이 긴 내용은 `references/`로 빼고 SKILL.md에서 파일명으로 가리킨다. 실행 가능한 스크립트·템플릿은 `assets/`에 둔다. SKILL.md 본문은 짧을수록 좋다.

## 구조

```
claude-skills/
  .claude-plugin/
    marketplace.json           카탈로그
  plugins/
    korean-gov-doc/
      .claude-plugin/
        plugin.json            플러그인 메타
      skills/
        korean-gov-doc/
          SKILL.md             진입점
          references/          상세 문서 (필요할 때만 읽힘)
          assets/              빌드 스크립트, 스타일 파일
```
