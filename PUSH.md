# 처음 푸시하는 법

이 폴더는 이미 git 저장소이고 커밋 1개가 들어 있습니다. 원격만 연결해 올리면 됩니다.

## 방법 A — gh CLI (설치돼 있으면 가장 간단)

```bash
cd claude-skills
gh repo create claude-skills --private --source=. --remote=origin --push
```

공개로 만들려면 `--private` 대신 `--public`.

## 방법 B — 웹에서 만들고 연결

1. github.com/new 에서 `claude-skills` 생성 (README·gitignore 체크 해제)
2. 아래 실행 (`<계정>` 자리에 본인 GitHub 아이디)

```bash
cd claude-skills
git remote add origin https://github.com/<계정>/claude-skills.git
git push -u origin main
```

## 확인

```
/plugin marketplace add <계정>/claude-skills
/plugin install korean-gov-doc@csw-skills
```

비공개 저장소면 설치하는 사람도 해당 저장소 접근 권한이 있어야 합니다.

## 커밋 작성자

초기 커밋 작성자가 Claude로 되어 있습니다. 본인 이름으로 바꾸려면:

```bash
git -c user.name="이름" -c user.email="메일" commit --amend --reset-author --no-edit
```

또는 `.git` 폴더를 지우고 다시 `git init` 해도 됩니다.
