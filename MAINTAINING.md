# 维护说明

## 目录约定

- `代码仓库`：源代码、前端资源、工作流和工具。
- `用户数据`：画布、历史、素材和生成结果，不提交到 Git。
- `API密钥`：本地 `.env` 和其他凭据，不提交到 Git。
- `便携运行环境`：本机使用的已配置 Python 运行时，不提交到 Git。
- `python`、`packages`：原作者公开仓库附带的基础 Python 和离线安装包，已随公司仓库完整保留；新电脑首次使用请运行 `安装依赖.bat`。

在 Windows 上请运行 `代码仓库\启动服务.bat`。脚本优先使用本机 `便携运行环境\python\python.exe`，没有时回退到仓库内的 `python\python.exe`；首次下载后如提示缺少模块，先运行 `安装依赖.bat`。运行数据写入上级目录的 `用户数据`，凭据写入上级目录的 `API密钥`。

## 远程仓库约定

- `upstream`：原作者仓库，仅用于查看、参考和恢复出厂版本，不用于日常开发或推送。
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

公司版本的日常更新、删减、新组件和发布都只在 `company/main`（或从它创建的功能分支）进行；不要把 `upstream/main` 设置为开发分支，也不要向 `upstream` 推送。
