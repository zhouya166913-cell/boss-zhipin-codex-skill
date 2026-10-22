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
<python> scripts/boss_safe.py --confirm-write -- recruiter greet <候选人ID> --job <岗位ID> --json
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
