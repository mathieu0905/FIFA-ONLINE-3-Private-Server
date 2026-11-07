# 完整增强源码 / Maintained enhanced source

本目录公开本机维护版本的服务端业务源码、当前与历史热包、客户端资源修改工具、配置模板以及开发回归脚本。它是源码分发目录，未附带本机存档或游戏资源。

安装前请先读 **[Windows 安装与增强功能准备教程](../INSTALL.zh-CN.md)**。当前没有面向任意原版客户端的完整增强首装器；教程给出基础可用路线、增强资源/发布依赖和只读条件检查。下载源码并不能直接启用全部增强功能。

`server/http_config.py` 已包含本机的增强模块安装链和热更新分派逻辑。当前活动业务源码见 [shop_cleanup_20261107_01/business.py](server/hot_updates/revisions/shop_cleanup_20261107_01/business.py)，路由表见 [active-business-source.json](active-business-source.json)。根目录的上游程序和历史继续保留；它们不会自动改为运行本目录。

## 已上传的功能和入口

| 功能 | 主要源码 |
| --- | --- |
| 动态随机开包、批量开包、旧库存兼容 | [活动业务包](server/hot_updates/revisions/shop_cleanup_20261107_01/business.py)、[draw_first.py](server/draw_first.py)、[draw_first_rules.json](server/draw_first_rules.json) |
| 最低保证强化档定价、统一标价和实际扣款 | 活动业务包中的 `pricing_data`、`pricing_host`、`pricing_dispatch` |
| 多轮连锁、整轮购买、独立限购与商品编排 | [chain_round_purchase.py](server/chain_round_purchase.py)、[product_packs.py](server/product_packs.py)、[pack_cadence.py](server/pack_cadence.py)、[pack_catalogue.py](server/pack_catalogue.py) |
| NPC 市场、供给、估值、上架和成交规则 | [market_simulation.py](server/market_simulation.py)、[market_price_store.py](server/market_price_store.py)、[fair_value_model.py](server/fair_value_model.py)、[fair_value_store.py](server/fair_value_store.py) |
| 强化、材料梯度、保护与设置 | [enhancement_progression.py](server/enhancement_progression.py)、[enhancement_protection40.py](server/enhancement_protection40.py)、[enhancement_settings.py](server/enhancement_settings.py) |
| 经验等级、经验道具和奖励 | [experience_levels.py](server/experience_levels.py)、[experience_items_ext.py](server/experience_items_ext.py)、[league_reward_guard.py](server/league_reward_guard.py) |
| 球员与赛季扩展、原生身份、模型骨骼与完整性检查 | [player_import](server/tools/player_import/README.md)、[roster_extension_hooks.py](server/roster_extension_hooks.py)、[wonderkid_runtime.py](server/wonderkid_runtime.py) |
| 全局球员数据库编辑器 | [player_editor](server/player_editor/)、[开发与界面回归](development/global-player-editor/) |
| 中文界面、图标、卡包说明和兼容修复 | [localization_zh.py](server/localization_zh.py)、[pack_descriptions.py](server/pack_descriptions.py)、[shop_icon_assets.py](server/shop_icon_assets.py) |
| AI 对手成长与离线挑战 | [ai_opponent_progression.py](server/ai_opponent_progression.py)、[offline_theme_challenges.py](server/offline_theme_challenges.py) |
| ABI 2 热更新、发布、回退与状态查询 | [hot_update_runtime.py](server/hot_update_runtime.py)、[hot_update_publish.py](server/hot_update_publish.py)、[hot_update_release.py](server/hot_update_release.py)、[hot_update_control.py](server/hot_update_control.py) |
| 客户端 UI/语言/资源补丁生成和安装校验源码 | [patches](server/patches/)、[开发工具与回归](development/)、[BIG 布局检查](server/tools/check_data0_layout.py) |

## 目录和完整性

- `server/`：正式目录的源码快照，包括真实安装链、管理页、全局球员编辑器和全部历史业务包源码。
- `config-templates/`：卡池、商品、连锁、限购、强化、市场、估值及球员注册表的配置模板。`shop.catalogue.json` 只包含商品目录字段。这里的 `.json.gz` 是自行生成的冻结 NPC 定价/估值输入，未包含真实玩家交易或市场运行数据库；`server/tools/value_v11/selected-model.json.gz` 是对应的训练后估值模型参数。
- `development/`：按功能保留的开发工具、补丁生成器、数据构建和回归脚本。它包含历史方案，不能按文件名排序后批量运行；当前实现以 `server/` 和活动业务包为准。
- `source-inventory.json`：每个导出文件的类别、来源内容哈希、公开文件哈希和是否脱敏。源文件未被修改；换行统一为 LF。一个用于拼接函数体的历史片段保留为 `.py.fragment`。
- `verification.json`：源码完整性、语法、配置哈希、压缩 JSON 脱敏和活动业务路由编译结果。

## 使用前需要准备什么

Python 3.12 及以上。上游运行依赖 `cryptography`；图标生成和模型训练等工具还有各自的依赖，应按对应源码准备。没有打包第三方 Python 环境。

需要使用者自备 FO3 ID 客户端、客户端资源和从自己的安装生成的数据库。球员身份、赛季和卡池与本机已有资源相关；只有提取原版数据库并不能自动生成所有自定义赛季。相关构建、导入、补丁生成和校验源码已提供，需要依据对应输入逐项构建。

本机路径仍保留在维护源码中，部分工具默认 `D:\FO3ID` / `D:\fifaol3`。运行安装器前必须核对路径、所需输入、发布基线和是否会中断游戏。`play-local.bat` 和 `patches/*_preflight.py` 是本机受保护安装链的源码，依赖本机历史发布回执和实际资源哈希；这些证书未复制进仓库，不能拿此快照直接覆盖正在游玩的安装。

可以在一个**全新输出目录**生成配置，交易签名密钥会为该输出重新生成：

```powershell
python -B tools/materialize_config_templates.py --output C:\FO3-work\fresh-config
```

这一步仅准备文本配置和冻结 NPC 估值输入，不安装客户端、不生成全部数据库、不注册热包或启动服务。不要把整目录覆盖到已有 `gamedata`；已有玩家的商品权益、回执、签名密钥及进度需要单独迁移。`player-imports.json` 中的资源来源/哈希记录也不是当前新机器的通过证书。

`active-business-source.json` 只公开当前业务版本和路由映射，不是可激活的 `active.json`。在使用者自己的资源和发布体系中完成校验并发布后，才会生成该安装自己的清单与回执。仓库未伪造历史哈希，也未绕过原生导入检查或发布保护。

## 验证与边界

在仓库根目录运行：

```powershell
python -B tools/validate_enhanced_sources.py
python -B -m unittest discover -s tests -p test_source_distribution.py -v
```

框架的隔离回归见 [enhancements/hot_update](../enhancements/hot_update/README.md)。此次公开过程没有启动第二套游戏服务，没有改动正式服务、存档、商城或客户端，也没有进行游戏 GUI 或比赛验收。

开发目录中的历史回归有本机绝对路径和安装动作；不要把它们当作统一的安全测试入口。源码语法/框架回归通过不代表每个历史脚本都能在任意目录直接运行，也不代表当前上游新版本与本机所有增强已经自动合并验收。

未上传：真实经理存档、卡实例、余额和库存，凭据和 TLS 私钥，游戏客户端、BIG/SWF/ABC、数据库文件、球员 3D 模型、贴图、音乐、原始抓包/转储、抓取网页、第三方依赖、本机备份和历史安装证书。补丁生成与资源处理的**源码逻辑**已包含。

All maintained enhancement logic is included as source, including the integrated local HTTP host and active business payload. Game assets, saves, secrets and machine-bound installation proofs are excluded. This is a source distribution; preparing a matching playable installation still requires the user's own resources, fresh keys, builds and validation. Upstream authorship and GPL-3.0 licensing are preserved.
