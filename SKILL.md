---
name: boss-zhipin
description: 安装、连接并安全使用 BOSS 直聘命令行能力，适用于招聘方查看岗位、搜索候选人、阅读简历、处理沟通与邀约，也支持求职者搜索职位；仅在用户明确要求操作 BOSS 直聘时使用。
---

# BOSS 直聘

通过本 Skill 自带的安全包装器调用社区维护的 `kabi-boss-cli`。BOSS 直聘没有面向公众的通用招聘开放 API；此方案依赖用户本人的登录态，不是 BOSS 直聘官方集成。

## 开始前

1. 明确用户要使用招聘端还是求职端；未说明但语境是招聘时，默认使用招聘端。
2. 不读取、展示、复制或提交 Cookie、Token、`credential.json` 及浏览器凭证数据库。
3. 不绕过验证码、风控、频率限制或平台安全机制，不承诺账号不会被限制。
4. 首次安装前说明：运行时会安装到用户目录下的隔离虚拟环境，不修改项目 Python 环境；当前固定依赖为 `jackwener/boss-cli` 的提交 `9d38ed1`。使用源码提交是因为已发布的 PyPI 包尚未包含招聘端命令。

## 连接流程

从本 Skill 根目录执行。Windows 优先使用 `py -3`，其他系统优先使用 `python3`；若不可用再尝试 `python`。

```text
<python> scripts/bootstrap.py check
<python> scripts/bootstrap.py install
<python> scripts/boss_safe.py -- login
<python> scripts/boss_safe.py -- status --json
```

- `check` 只检查环境，不安装依赖、不访问 BOSS。
- `install` 创建隔离运行时并安装固定版本依赖。
- `login` 必须由用户本人完成扫码或浏览器登录。不要索要 Cookie 文本。
- `status` 成功后，再执行实际业务命令。
- 如果 Python 低于 3.10、安装失败或登录失败，读取 [references/troubleshooting.md](references/troubleshooting.md)。

## 执行招聘任务

读取 [references/commands.md](references/commands.md) 中的招聘端部分，只调用完成当前任务所需的最少命令。优先使用 `--json` 获取结构化结果；向用户展示结果时隐藏内部 ID、手机号、微信号和其他不必要的个人信息。

典型只读顺序：

```text
<python> scripts/boss_safe.py -- recruiter jobs --json
<python> scripts/boss_safe.py -- recruiter recommend --job <岗位ID> --json
<python> scripts/boss_safe.py -- recruiter resume <候选人ID> --job <岗位ID> --json
```

先读取，再分析，最后才提出沟通建议。不得因为用户要求“自动招聘”就默认批量联系、批量查看、批量下载或自动淘汰候选人。

## 写操作规则

发送消息、发起沟通、请求简历或联系方式、邀约面试、标记不合适、上下线岗位、退出登录以及导出候选人数据，都属于有副作用的操作。

执行前必须：

1. 向用户列出准确对象、动作和将发送的完整文本；
2. 在当前对话中取得明确确认；
3. 仅对已确认的对象执行，不扩大范围；
4. 调用包装器时添加 `--confirm-write`。

示例：

```text
<python> scripts/boss_safe.py --confirm-write -- recruiter reply <friendId> "已确认的消息" --yes --json
```

批量操作还必须先执行上游命令的 `--dry-run`，展示目标数量和范围；用户再次确认后才可增加 `--allow-batch`。不得在后台持续轮询、自动回复或无人值守批量联系。

## 数据与输出

- 默认只在终端展示必要字段，不落盘保存简历或聊天记录。
- 用户明确要求导出时，先说明目标路径、字段和数据敏感性，再以 `--confirm-write` 执行。
- 禁止将候选人数据、凭证文件、日志和导出结果加入 Git、上传到公开仓库或发送给无关第三方。
- 遇到接口变更、验证码、访问频率限制或会话异常时停止，不尝试规避；按故障排查文档处理。

## 求职端

只有在用户明确以求职者身份操作时，才使用 [references/commands.md](references/commands.md) 中的求职端命令。批量打招呼遵守与招聘端相同的预览、确认和限量规则。
