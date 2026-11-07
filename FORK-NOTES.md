# FIFA Online 3 增强版 / Enhanced fork

本仓库 Fork 自 [soloplayer24/FIFA-ONLINE-3-Private-Server](https://github.com/soloplayer24/FIFA-ONLINE-3-Private-Server)。原项目由 soloplayer24 及其贡献者开发；本 Fork 在其基础上整理新增代码和维护说明，不将原项目成果归为本 Fork 原创。

Original project: soloplayer24 and contributors. This fork preserves the upstream Git history and LICENSE (GPL-3.0). Fork additions are distributed under the same license.

## 本次已公开的新增代码

`enhancements/hot_update/` 包含本机维护版本中的以下源码：

- ABI 2 业务热更新运行时：固定业务路由、三个受限动态模板、逐请求参数隔离、旧请求保留原处理函数。
- 加载前校验：代码哈希、发布清单、回执、路由边界和允许的函数定义结构。
- 发布事务：共享锁、当前版本核对、备份、逐文件并发检查及失败回退。
- 状态查询、业务回退和停用命令的源码。
- 使用临时目录、模拟宿主和本地 socket 的框架回归脚本。

这些模块尚未接入本仓库当前的上游 HTTP/管理页启动链。下载本仓库并不会自动获得业务热更新能力。发布器依赖本机发布体系的 `play-local.bat`、`patches/*_preflight.py`、`compose_manifest`、guards 和 receipt policies；这些安装链及业务包尚未移植。本目录是可审阅的框架源码，不能直接作为上游的一键安装器。

## 本机增强功能的整理进度

以下是本机维护范围，**尚未随本次提交完整公开或接入本仓库**：

| 功能 | 公开状态 |
| --- | --- |
| 动态随机开包、批量开包与连锁礼包 | 业务实现与商品配置待整理 |
| 按最低保证强化档定价，高强化作为额外奖励 | 定价业务包与扣款链待整理 |
| 球员导入完整性校验、原生身份与模型路由检查 | 工具及可公开的输入边界待整理 |
| 市场供给、更多球员与赛季扩展 | 依赖梳理与可分发范围待整理 |

后续移植需要逐项核对与上游新版的差异，不用旧本机文件整包覆盖上游。只有实际提交并通过相应验证的功能才会改为“已公开/已接入”。

## 验证范围

框架回归只证明临时数据中的加载、切换和发布事务行为。它不证明真实客户端显示、完整商城业务、比赛或新增球员模型通过。具体运行方法及依赖见 [框架说明](enhancements/hot_update/README.md)。

## 内容边界

此次提交只增加列明的 Python 源码、测试和说明。未从本机上传真实经理存档、余额、卡片、库存、账号凭据、TLS 私钥、日志、抓包、客户端、BIG、数据库、模型或音乐。上游原有文件及历史保留；原始文档中的外部链接不代表本 Fork 新增上传了对应资源。
