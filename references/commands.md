# 命令参考

所有命令都从 Skill 根目录通过安全包装器执行。以下用 `<python>` 表示当前平台可用的 Python 3.10+ 命令。

## 招聘端只读操作

```text
<python> scripts/boss_safe.py -- recruiter jobs --json
<python> scripts/boss_safe.py -- recruiter search "Python" --city 杭州 --exp 3-5年 --json
<python> scripts/boss_safe.py -- recruiter recommend --job <岗位ID> --json
<python> scripts/boss_safe.py -- recruiter inbox --job <岗位ID> --json
<python> scripts/boss_safe.py -- recruiter chat <friendId> --json
<python> scripts/boss_safe.py -- recruiter geek <候选人ID> --job-id <岗位数字ID> --json
<python> scripts/boss_safe.py -- recruiter resume <候选人ID> --job <岗位ID> --json
<python> scripts/boss_safe.py -- recruiter labels --json
```

先用 `jobs` 获取真实岗位 ID，不要猜测 ID。搜索结果和简历只展示完成当前任务必要的字段。

## 招聘端写操作

以下命令必须先向用户展示对象与动作并取得明确确认，再添加 `--confirm-write`：

```text
<python> scripts/boss_safe.py --confirm-write -- recruiter greet <候选人ID> --job <岗位ID> --security-id <安全ID> --expect-id <期望ID> --lid <推荐链路ID> --message "已确认或已授权生成的招呼语" --json
<python> scripts/boss_safe.py --confirm-write -- recruiter reply <friendId> "已确认的消息" --yes --json
<python> scripts/boss_safe.py --confirm-write -- recruiter request-resume <friendId> --yes --json
<python> scripts/boss_safe.py --confirm-write -- recruiter exchange-phone <friendId> --yes --json
<python> scripts/boss_safe.py --confirm-write -- recruiter exchange-wechat <friendId> --yes --json
<python> scripts/boss_safe.py --confirm-write -- recruiter invite-interview <候选人ID> --job <岗位ID> --address "已确认的地点" --time "已确认的时间" --desc "已确认的说明" --yes --json
<python> scripts/boss_safe.py --confirm-write -- recruiter mark-unsuitable <候选人ID> --job <岗位ID> --yes --json
<python> scripts/boss_safe.py --confirm-write -- recruiter job-close <岗位ID> --yes
<python> scripts/boss_safe.py --confirm-write -- recruiter job-reopen <岗位ID> --yes
```

不要自行补齐未知参数。先运行对应命令的 `--help`，再根据用户提供的信息构造命令。

`recruiter greet` 已由 `scripts/boss_cli_compat.py` 修复为网页“打招呼”按钮对应的真实发起沟通请求。岗位 ID、候选人 ID、`securityId`、`expectId` 和 `lid` 都必须来自本次只读岗位/推荐结果，不能猜测，也不向用户索要。只有结构化结果为 `ok=true` 且 `data.geekId` 存在时才报告发送成功；旧版命令仅查看候选人，不得把查看结果当成打招呼。

用户已给出 `SKILL.md` 所定义的一次性自动招呼授权时，可以在当前岗位和人数上限内顺序调用上述命令，不再逐人询问；每次仍使用 `--confirm-write`，并在任何一次失败后停止剩余发送。

## 批量查看

`batch-view` 会让候选人侧出现“被查看”痕迹，虽然不发送文本，也按远程写操作处理。

```text
# 第一步：只预览
<python> scripts/boss_safe.py --confirm-write -- recruiter batch-view "Python" --city 杭州 -n 5 --dry-run

# 第二步：用户再次确认后执行
<python> scripts/boss_safe.py --confirm-write --allow-batch -- recruiter batch-view "Python" --city 杭州 -n 5 --yes
```

## 敏感数据导出

导出和简历下载会在本地新增包含个人信息的文件，必须确认目标路径，确保路径位于非公开、未被 Git 跟踪的目录。

```text
<python> scripts/boss_safe.py --confirm-write -- recruiter export --format json -o <安全路径>
<python> scripts/boss_safe.py --confirm-write -- recruiter resume-download <候选人ID> --job <岗位ID> -o <安全路径>
```

## 求职端只读操作

```text
<python> scripts/boss_safe.py -- search "AI 产品经理" --city 上海 --json
<python> scripts/boss_safe.py -- detail <securityId> --json
<python> scripts/boss_safe.py -- recommend --json
<python> scripts/boss_safe.py -- applied --json
<python> scripts/boss_safe.py -- interviews --json
<python> scripts/boss_safe.py -- chat --json
```

## 求职端写操作

```text
<python> scripts/boss_safe.py --confirm-write -- greet <securityId> --json

# 批量打招呼必须先预览，再由用户二次确认
<python> scripts/boss_safe.py --confirm-write -- batch-greet "Python" --city 杭州 -n 5 --dry-run
<python> scripts/boss_safe.py --confirm-write --allow-batch -- batch-greet "Python" --city 杭州 -n 5 --yes
```
