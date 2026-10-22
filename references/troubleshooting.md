# 故障排查

## Python 不可用

要求 Python 3.10 或更高版本。依次检查：

```text
py -3 --version
python3 --version
python --version
```

不要替用户静默安装系统级 Python。说明缺失项并让用户选择安装方式。

## 运行时未安装

先执行只读检查：

```text
<python> scripts/bootstrap.py check
```

若 `installed` 为 `false`，说明将从 GitHub 安装锁定的 `jackwener/boss-cli` 源码提交到输出中的 `runtime_root`，然后执行：

```text
<python> scripts/bootstrap.py install
```

不要把运行时建在仓库内，也不要修改项目依赖文件。

## 登录失败

1. 确认用户可以在普通浏览器中正常打开并登录 `https://www.zhipin.com/`。
2. 执行 `<python> scripts/boss_safe.py -- login --qrcode`，由用户本人扫码。
3. 如果二维码登录缺少浏览器生成的会话信息，改用专用浏览器配置登录，再执行 `login`。
4. 不让用户把 Cookie 或 Token 粘贴到聊天中，不读取浏览器凭证数据库内容。

## Windows 浏览器 Cookie 无法读取

新版 Chrome/Edge 可能阻止外部程序解密 Cookie。优先使用二维码登录。只有用户明确同意时，才按照上游工具提示使用独立浏览器配置和本机回环 CDP；不得连接非回环 CDP 地址。

## code 37、登录过期或接口变化

先执行：

```text
<python> scripts/boss_safe.py -- status --json
```

若登录失效，重新由用户扫码。若登录正常但业务接口持续失败，停止写操作并报告具体命令、退出码和已脱敏的错误信息。不要通过伪造指纹、提高请求频率、验证码求解或改写安全参数规避限制。

## 写操作被包装器阻止

- `--confirm-write` 缺失：先向用户展示准确对象、动作和文本并取得确认。
- `--allow-batch` 缺失：先执行 `--dry-run`，展示批量范围并取得第二次确认。
- 不要修改包装器来绕过这些保护。
