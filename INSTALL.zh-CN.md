# Windows 安装与增强功能准备教程

## 先回答：下载后能不能直接使用增强功能？

**当前不能下载后直接获得全部增强。** 本仓库已经公开完整增强源码，但还没有面向任意原版客户端的完整增强首装器，也没有分发本机配套的游戏资源。普通用户可以按下面的基础路线运行上游版本；开发者拥有匹配资源并完成初始化、发布和验收后，才能使用完整增强。

| 你拥有的内容 | 当前可以做到什么 |
| --- | --- |
| 只有下载的仓库，没有 FO3 ID 客户端 | 阅读源码、运行隔离回归；不能玩游戏 |
| 仓库 + 兼容的 FO3 ID 原版客户端 | 按基础路线安装上游服务；不会自动获得本机全部增强 |
| 仓库 + 已构建的配套增强客户端、球员数据库和资源 | 按进阶路线准备自己的配置/市场库/发布凭据，逐项校验后运行增强服务 |
| 已有自己的角色存档或旧私服 | 需要单独迁移与备份；不能把模板或别人的数据库/存档整包覆盖进去 |

GitHub 页面显示 Fork 来源，代码保留上游的 GPL-3.0 许可。**“增强源码已上传”不等于“完整增强安装包已交付”。**

## 一、环境与下载

需要 Windows、Python 3.12 或更高版本、兼容的 FIFA Online 3 印尼版客户端（上游针对 build 654420），以及生成本机 TLS 证书所需的 OpenSSL。图标生成工具另外使用 Pillow；估值训练等开发工具的依赖按其源码准备，不是基础运行必需项。

使用 Git 下载：

```powershell
git clone https://github.com/mathieu0905/FIFA-ONLINE-3-Private-Server.git C:\FO3-work\source
Set-Location C:\FO3-work\source
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install cryptography
```

没有 Git 时，在仓库页面点 **Code → Download ZIP**，解压后进入仓库根目录，再执行创建 `.venv` 和安装依赖的两行命令。根目录应能看到 `README.md`、`INSTALL.zh-CN.md`、`enhanced` 和 `tools`。如果安装的 Python 版本更高，可把 `py -3.12` 换成对应版本。

以下示例用 `C:\FO3-work\source` 存放源码、`C:\FO3-client` 存放自己的客户端。实际路径可以不同。教程中的命令由使用者在自己的机器上执行；仓库发布过程没有替你安装游戏或提供客户端下载。

## 二、基础路线：先运行上游原版功能

这一节操作**仓库根目录**的程序。根目录的 `play.bat`、`start_all.py` 不会自动切换到 `enhanced/server`。

### 1. 设置客户端路径并提取数据库

先确认 `C:\FO3-client\fifazf.exe` 和 `C:\FO3-client\data\data_0.big` 存在，然后在仓库根目录运行：

```powershell
$env:FO3_GAME = 'C:\FO3-client'
$env:FO3_LANGUAGE = 'ind'
.\.venv\Scripts\python.exe -B extract_fifadb.py C:\FO3-client
```

成功后应生成根目录下的 `gamedata\fifadb.sqlite`，命令输出数据库路径和球员行数。提取失败时先核对客户端版本和资源是否匹配，不要用空库继续。只提取原版数据库，不会创建自定义球员或赛季。

### 2. 生成本机 HTTPS 证书

先用 `openssl version` 确认 OpenSSL 命令可用。仍在仓库根目录运行：

```powershell
New-Item -ItemType Directory -Path certs -Force
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=APSEODESK172" -addext "subjectAltName=DNS:APSEODESK172" -keyout key.pem -out cert.pem
.\.venv\Scripts\python.exe -c "from pathlib import Path; Path('certs/server.pem').write_bytes(Path('cert.pem').read_bytes()+Path('key.pem').read_bytes())"
```

应生成 `certs\server.pem`。`key.pem`、`server.pem` 含自己的私钥，不要上传仓库、发给其他人或与别人共用。增强服务位于另一个目录时，应在那个服务目录生成它自己的 `certs\server.pem`。

### 3. 添加本机域名映射

以管理员身份打开记事本，编辑：

```text
C:\Windows\System32\drivers\etc\hosts
```

确认有这一行；已有相同映射时不要重复添加：

```text
127.0.0.1 APSEODESK172
```

客户端使用该域名访问 HTTPS API。保存后可在 PowerShell 运行 `ping APSEODESK172`，确认解析到 `127.0.0.1`。

### 4. 启动服务

在一个 PowerShell 窗口中，从仓库根目录运行：

```powershell
$env:FO3_GAME = 'C:\FO3-client'
$env:FO3_LANGUAGE = 'ind'
.\.venv\Scripts\python.exe -B start_all.py
```

保留窗口。预期有 HTTPS API `443`、管理页面 `8088` 和 messenger `28002`；管理页地址为 <http://127.0.0.1:8088/>。检查日志中是否有 traceback 或子进程退出；管理页能打开不等于游戏登录已通过。

如果端口已被你正在运行的游戏服务占用，使用现有服务或等自己的会话结束后再处理，不要叠加启动第二套服务。

### 5. 启动自己的客户端

在第二个 PowerShell 窗口中，从仓库根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\launch_game.ps1 -Exe C:\FO3-client\fifazf.exe
```

该脚本传入本地服务器参数，窗口会保留到客户端返回。客户端本身仍须能正常完成它自己的初始化。

也可以按 [上游启动器说明](launcher/fifalauncher.cs)编译启动器；源码中的 `csc.exe` 命令必须在相应目录执行，客户端路径也要核对。基础教程使用上面的显式 `-Exe` 路径，避免把默认 `D:\FO3ID` 当作每个人的安装路径。

### 6. 基础验收

依次确认管理页、游戏登录、经理选择、首页和一场比赛。基础路线是否成功以自己的客户端实测为准。**这一路线使用上游功能，不会自动启用本 Fork 的动态开包、全新定价和扩展球员。**

## 三、完整增强路线：先检查条件，再准备资源

本节面向维护者/开发者。**目前缺少把任意原版客户端一键构建为完整增强版的统一首装器。** 下列步骤给出实际目录、必需输入、校验和启动顺序；标成“需要构建/适配”的步骤不能跳过，也没有用一条复制命令替代它。

增强服务源码入口：

```text
C:\FO3-work\source\enhanced\server
```

可在本机安装工作目录使用该树，但不要把它覆盖到正在运行的服务。`enhanced\development` 保存大量历史安装/回归脚本；其中一些硬编码 `D:\FO3ID` / `D:\fifaol3`，有的会安装资源或操作服务。不能按文件名排序批量执行，也不能把里面的 `test.py` 当作统一的安全测试入口。

### 1. 运行只读安装条件检查

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -B tools\check_enhanced_install.py --server C:\FO3-work\source\enhanced\server --client C:\FO3-client
```

该命令不启动服务、不读取经理存档、不写游戏文件，也不会自动创建缺失的 SQLite。刚下载时输出 **`NEEDS_PREPARATION`** 是预期结果；退出码为 `2`，每个失败项会说明缺什么。

| 检查项 | 缺失时需要做什么 |
| --- | --- |
| `enhanced-source` | 指定 `enhanced\server` 或自己的增强服务目录，不是上游根目录；确认源码完整 |
| `client-files` | 准备自己的兼容客户端以及 `data_0/3/4/6.big` |
| `tls-certificate` | 在增强服务目录按基础路线生成本机证书 |
| `configs-and-keys` | 按下一步生成自己的配置；不能直接使用脱敏占位符 |
| `player-database` | 构建匹配自定义赛季/球员的数据库；原版提取不包含这些卡 |
| `market-database` | 在匹配球员数据库上初始化 NPC 价格和估值数据库，绑定本机路径 |
| `client-shop-icons` | 构建/准备清单对应的图标文件；存在文件还需核对哈希 |
| `local-release-chain` | 为这个安装建立真实的发布基线、guards 和回执；仓库没有本机历史证书 |
| `active-business-proof` | 在自己的发布链上发布活动业务包，生成有效 `hot_updates\active.json` |
| `native-import-certificate-present` | 完整原生导入检查通过后生成这个安装自己的证书 |

所有前置项存在时，工具只会报告 `PREREQUISITES_PRESENT_NATIVE_PENDING`，仍不代表完整发布预检、原生球员校验、游戏或比赛验收通过。`--hash-assets` 可以增加图标哈希核对。

### 2. 生成新安装的配置和签名密钥

从仓库根目录运行，输出目录必须尚不存在：

```powershell
.\.venv\Scripts\python.exe -B tools\materialize_config_templates.py --output C:\FO3-work\fresh-gamedata
```

输出包含商品、卡池、强化、市场、注册表和冻结 NPC 定价输入。两个交易签名密钥会重新生成，对应配置内容哈希也会更新。不会生成 `state.json`，不会生成球员数据库或 NPC 市场 SQLite。

对于**没有存档的全新安装**，构建流程应把这些文件放入自己的增强服务 `gamedata`，再补全下表中的资源。若 `gamedata` 已存在，先检查其内容并按自己的迁移事务处理，不要整目录覆盖。已有存档迁移时也不要用新密钥替换旧密钥，否则旧库存令牌/回执可能不兼容。

### 3. 必须构建/适配的配套内容

| 内容 | 最终位置/要求 | 已公开的处理源码 |
| --- | --- | --- |
| 自定义赛季和球员 UI 数据 | 服务端 `gamedata/fifadb.sqlite` 与客户端 UI 库、语言姓名一致 | `development` 下的 `build_bulk_seasons.py`、`compose_seasons.py` 及各赛季目录 |
| 原生球员身份、脸型/骨骼/模型 | 原生 `players` 身份、五件套或明确通用脸型、六语言、头像和注册表一致 | [player_import 工作流](enhanced/server/tools/player_import/README.md)，`prepare.py`、`check.py` |
| NPC 市场初始数据库 | `gamedata/npc-market-prices.sqlite`，估值 profile 与本机球员库一致 | `market_price_store.initialize/apply_calibration`、`fair_value_store.install_catalogue`、各赛季价格扩展源码 |
| 商城图标 | 客户端 `_cache/games/fo3id/externalAssets/shop`，文件名与清单 SHA256 匹配 | `development/item-icons`、`development/draw-first` 等生成工具 |
| 中文和扩展 UI | 对应客户端语言/UI/BIG；例如强化、批量开包、连锁和球员详情 | `development` 下对应功能的补丁生成器；`server/patches` 中的校验源码 |
| 新安装的发布基线 | 自己的 `play-local.bat`、preflight、manifest、receipt、全部 guards/receipt policies | `hot_update_release.py` 和 `patches/*_preflight.py` 提供参考逻辑；**通用首装基线生成器尚未提供** |

上述市场初始化是开发 API，不是一条适用于任意原版球员库的安装命令。冻结定价输入依赖匹配的 SPID、球员属性和估值版本；只初始化最早的 seed，会遗漏后续赛季和最终估值链。不要把别人的运行市场 SQLite 当作自己的初始数据库。

配套的球员 3D 模型、头像、游戏语言/UI/BIG、原始数据库等没有随仓库分发，需要使用者准备有来源的输入并构建。`custom_rosters.json`、`player-imports.json` 和图标清单描述的是依赖，复制这些 JSON 不会产生对应资源。**如果你只有原版客户端，当前应在这里停下，不能宣称完整增强已经安装。**

### 4. 完整原生导入检查

配套资源、双端数据库、来源注册和模型路线都准备完成后，以下命令在**自己的增强服务目录**执行；Python 路径按实际环境调整：

```powershell
C:\FO3-work\source\.venv\Scripts\python.exe -B tools\player_import\check.py --server C:\FO3-work\source\enhanced\server --client C:\FO3-client --full
```

通过后，发布流程可在同一完整输入上增加 `--write-certificate <自己的证书输出路径>` 生成本机证书，并将证书纳入同一真实发布事务。不能直接复制原机器证书、篡改历史哈希或删除缺资源球员来让检查通过。证书通过仍需分别验收首页近景、远景、带球、比赛加载和动画。

### 5. 在自己的发布链上启用活动业务包

当前公开的完整活动业务包为：

```text
hot_updates/revisions/shop_cleanup_20261107_01/business.py
```

完整的 7 条路由映射见 [active-business-source.json](enhanced/active-business-source.json)。它包括商城列表/限购/购买、连锁报价/购买、动态开包和市场供给。**不要只发布 `/shop/list`，否则可能只改标价而没有接入真实扣款。**

`active-business-source.json` 是源码路由说明，不是可激活的 `active.json`。需先完成自己的受保护安装基线，再依据 [热更新说明](enhanced/server/docs/hot-update.md)使用发布工具为本机生成不可变业务包、manifest、receipt 和活动描述符。发布器仍含本机默认路径，跨机器使用前必须适配并回归。不能绕过发布器手写一个“假通过”的活动描述符。

若尚未建立自己的发布链，此步骤当前无法直接执行；源码公开不代表通用首装流程已经补齐。这也是普通原版客户端下载后暂时无法直接使用完整增强的原因之一。

### 6. 发布预检、启动和运行时确认

完成自己的发布链后，先执行 `play-local.bat` 实际指向的 preflight 和独立 `player_import` 检查。路径均应指向自己的安装。只读条件检查不是完整 preflight 的替代品。

预检通过、当前没有正在进行的游戏会话时，在自己的增强服务目录设置客户端环境变量并启动其 `start_all.py`。沿用基础路线的启动形式，明确切换目录；不要同时保留上游根目录的服务。

服务启动后，在**同一增强服务目录**运行：

```powershell
C:\FO3-work\source\.venv\Scripts\python.exe -B hot_update_control.py
```

必须看到本机实际发布的完整业务 revision、`abi=2`、`watcher_running=true`、`error=null`。如果你按独立安装流程给业务包用了新的唯一 revision，以该 revision 为准；再次运行只读条件检查工具时，加上 `--expected-revision 你的实际唯一版本号`，路由仍须完整。

`bootstrap` 或空路由只表示框架已运行，不代表动态开包、批量开包和统一定价已经启用。管理页可访问或商城标价正确，也不能代替真实事务验证。

### 7. 增强验收清单

先用临时数据验证购买扣款、发包、限购、重复请求、失败回滚和并发；不要往真实存档写测试卡或测试余额。再由使用者确认：

- 进入经理选择、首页、背包、商城，显示和操作正常。
- 动态开包和批量开包正常；已有旧包的内容和概率未被改写。
- 随机包以最低保证强化档定价；标价、报价和实际扣款一致。
- 连锁单档/整轮、限购和重复请求行为符合预期。
- 市场供给、上架、成交及重启后持久化正常。
- 新球员的首页近/远景、带球和比赛正常。
- 强化、经验、阵容和赛后奖励正常；真实资产和后续进度保留。

在这些步骤完成前，不能把源码语法或接口通过写成整套实机通过。

## 四、常见问题

| 现象 | 排查方向 |
| --- | --- |
| 下载后运行 `play.bat` 看不到增强 | 根目录仍是上游程序；完整增强源码在 `enhanced/server`，并且还需要配套输入和发布 |
| `__GENERATE_LOCALLY__` / `fromhex` 错误 | 使用了脱敏模板；用配置生成工具准备全新安装配置，不能照抄占位符 |
| `unable to open database file` / 缺少 `metadata`、`prices` 表 | 球员库或 NPC 市场库未构建；配置 JSON 不能替代 SQLite |
| 缺少卡池球员 / SPID / native identity | 原版库不包含自定义赛季，或 UI 与原生身份没有一起导入；补齐资源与注册，不删卡消错 |
| `Missing or unverified shop image` | 缺少对应图标或哈希不匹配；按清单生成/安装，不能跳过校验 |
| 找不到 `*-installed.json` / `*-receipt.json` | 快照中的 `play-local.bat` 引用了原安装历史链；需要为新安装建立真实基线 |
| 热更新状态是 `bootstrap` 或旧版本 | 活动业务包未发布/未激活；检查本机描述符、回执、watcher 和 error |
| `443` / `8088` / `28002` 端口占用 | 检查现有服务，避免重复启动；不要为了安装打断正在玩的会话 |
| 首页黑屏、模型或比赛崩溃 | 回到双端数据库、原生身份、语言、模型/LOD/骨骼及客户端 UI 的完整校验 |

## 五、本教程验证了什么

本次检查了源码中的路径、命令入口、配置生成、热更新状态要求和资源依赖；新增只读条件检查工具有临时数据回归，确保缺文件时不误报成功、不创建缺失数据库、SQLite 只读、占位密钥会被拒绝。

没有在一台全新机器上完成完整增强首装，也没有在仓库发布过程中运行第二套游戏服务或操作真实存档/客户端。基础路线取自保留的上游安装说明；完整增强路线明确保留尚缺的配套资源和通用首装环节。后续补齐首装器并经过新机验收后，应更新本页顶部的支持状态。
