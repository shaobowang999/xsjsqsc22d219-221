# 维护说明

## 目录约定

- `代码仓库`：源代码、前端资源、工作流和工具。
- `用户数据`：画布、历史、素材和生成结果，不提交到 Git。
- `API密钥`：本地 `.env` 和其他凭据，不提交到 Git。
- `便携运行环境`：便携 Python 和第三方运行时，不提交到 Git。

在 Windows 上请运行 `代码仓库\启动服务.bat`。脚本会自动使用 `便携运行环境\python\python.exe`，并将运行数据写入上级目录的 `用户数据`，将凭据写入上级目录的 `API密钥`。

## 远程仓库约定

- `upstream`：原作者仓库，仅用于查看和参考。
- `company`：三千思创自己的 GitHub 仓库：`https://github.com/shaobowang999/xsjsqsc22d219-221`。

添加公司远程仓库：

```powershell
git remote add company https://github.com/shaobowang999/xsjsqsc22d219-221.git
git push -u company main
```

## 日常开发

```powershell
git checkout -b feature/<name>
# 修改并测试
git add <files>
git commit -m "描述修改内容"
git push -u company feature/<name>
```

同步上游时只读取，不直接合并或发布：

```powershell
git fetch upstream
git log --oneline --decorate --all -20
```
