# FIFA Online 3 增强版 / Enhanced fork

本仓库 Fork 自 [soloplayer24/FIFA-ONLINE-3-Private-Server](https://github.com/soloplayer24/FIFA-ONLINE-3-Private-Server)。原项目由 soloplayer24 及其贡献者开发；本 Fork 在其基础上整理新增代码和维护说明，不将原项目成果归为本 Fork 原创。

Original project: soloplayer24 and contributors. This fork preserves the upstream Git history and LICENSE (GPL-3.0). Fork additions are distributed under the same license.

## 完整增强源码已公开

此前只上传框架的范围已经扩展。完整源码入口为 **[enhanced/README.md](enhanced/README.md)**，包括本机已接入的 HTTP 服务、全部增强模块、当前及历史业务热包、配置模板、客户端补丁生成工具、球员导入和全局编辑器，以及按功能整理的开发与回归脚本。

动态开包、批量开包、最低保证强化档定价及实际扣款、连锁礼包、市场供给与估值、强化保护、经验等级、AI 对手、球员/赛季扩展、中文和客户端 UI 修复等逻辑均已包含，详见入口中的源码对应表。

根目录保留上游程序；增强版实际维护源码位于 `enhanced/server/`。该目录中的 HTTP 服务已经包含本机增强安装链，不能与“上游根目录已自动接入并完成整套游戏验收”混为一谈。

安装与可用范围见 [Windows 安装教程](INSTALL.zh-CN.md)。目前尚无适配任意原版客户端的完整增强首装器；新增的 `tools/check_enhanced_install.py` 只读列出资源、数据库、密钥和发布凭据缺项，不会把源码下载成功当作增强安装成功。

## 验证范围

此次完成源码清单及哈希核对、Python 语法检查、配置哈希与脱敏检查、活动业务路由编译、框架隔离回归和配置生成保护回归。没有启动游戏服务或操作真实资产。没有在新机器上完成客户端、商城、球员模型或比赛验收。验证报告见 `enhanced/verification.json`，框架运行方法见 [框架说明](enhancements/hot_update/README.md)。

## 内容边界

公开全部增强源码和去除凭据的配置模板；真实存档、游戏资源、原始抓取数据和本机安装证书未上传。交易签名密钥须在使用者自己的安装中生成。上游原有文件及历史保留；原始文档中的外部链接不代表本 Fork 新增上传了对应资源。
