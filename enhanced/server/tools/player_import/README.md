# 新球员导入与验收约定

## 本次故障留下的规则

首页切贝林时的真实 dump 显示 `0x008fd780` 读地址 `4`，当前查询为
`SELECT * FROM trainingteamplayers WHERE playerid = 252371`。引擎先查
`players`，找不到身份后查不存在的训练表并解引用空指针。UI 的 SQLite
有这张卡、名字和头像，并不能证明 3D 引擎能够加载这个球员。

每个新身份必须同时具备：

1. 服务端 `gamedata/fifadb.sqlite` 的卡片、权限及姓名数据。
2. 客户端 `data/db2/fifadb.db.db2` 的同一份 UI 数据；六语言库有该身份姓名。
3. `data/db/fifa_ng_db.db` 的原生 `players` 记录。主键是 playerid，不能把每个赛季的 SPID 当成不同原生球员；同一身份多张卡只补一条。
4. 明确的外貌路线：专属模型必须有 head/hair/hairLOD/face texture/hair texture；通用脸型必须明确记录类别、编号和已存在资源，不能冒称真人脸。
5. 注册表、头像、Lua 保留选择器以及原生 headassetid/headtype/headclass 的一致映射。

不要创建空训练表、忽略 SQL 错误、删除球员、替换成另一个球员，或恢复旧存档来绕过缺项。

## 字段和资源语义

- 原生 EA 库的整数按 meta 的 rangelow 编码，浮点按 IEEE32，日期按 EA Gregorian 日数编码。逐字段验证范围和实际位宽，不能直接把 SQLite 字节复制过去。行数是 UInt16，超过 65535 必须拒绝发布。
- 来源页面 1～5 星必须显式调用 `native_db.stars_to_code` 转为 0～4。逆足字段使用自己的范围，不能套用同一个减一规则。现存 FO3 特殊模板值不能未经来源核对就批量改写。
- UI 保留选择器 30001 等不是原生 headtype。专属模型在原生库使用 headassetid=本人资源 ID、headtype=1023、headclass=0；Lua/UI 路线另行保存。
- 不能靠 `.rx3` 扩展名、可打开或骨骼数量就认定兼容。已核对的 FIFA14_Switch 255 骨骼资源使用 `rig-map.json` 的逐名/作者别名映射转到原生 ImpactEngine 252；未知加权骨骼或未知来源 rig 直接拒绝。
- 转换只改 blend indices/weights、骨骼重映射和 bind pose；位置、法线、UV、三角索引、材质、贴图和内层 RX3 布局保持。合并同骨骼权重时保留整数权重总和。近景和远景都必须检查。
- data0 中间成员不得 append 后重指针。按目录顺序重建，所有非目标成员的原压缩字节及 packed/unpacked 大小必须相同，再运行 `tools/check_data0_layout.py`。

## 后续导入流程

已有 UI 导入器先生成同一工作产物中的 SQLite、data0（含六语言姓名）、注册表和头像。生成产物不是另开游戏环境，也不要把 fixture 写进真实资产。

`prepare.py` 接收这些产物及明确的模型包，把原生记录、完整五件套、rig 转换、Lua 选择器和资源回执合并到新的工作产物目录。它从不写正式目录。`source_skill_stars` 或 `skill_input: "fo3-code"` 必须显式声明；范围错误必须先修源语义，禁止静默截断。

模型包示意（五个文件均须填写本人来源和实际 SHA256）：

```json
{
  "schema": 1,
  "players": [{
    "playerid": 123456,
    "spid": 13123456,
    "name": "球员姓名",
    "source_rig": "FIFA14_Switch",
    "source_skill_stars": 4,
    "files": {
      "head_123456_0.rx3": {"path": "完整本地路径", "sha256": "实际哈希"},
      "hair_123456_0_0.rx3": {"path": "完整本地路径", "sha256": "实际哈希"},
      "hairlod_123456_0_0.rx3": {"path": "完整本地路径", "sha256": "实际哈希"},
      "face_123456_0_0_0_0_0_0_0_0_textures.rx3": {"path": "完整本地路径", "sha256": "实际哈希"},
      "hair_123456_0_textures.rx3": {"path": "完整本地路径", "sha256": "实际哈希"}
    }
  }]
}
```

```powershell
.venv\Scripts\python.exe -B tools\player_import\prepare.py `
  --spec D:\工作目录\player.json --server D:\FO3ID\server --client D:\FO3ID\32795 `
  --database D:\工作目录\UI产物\fifadb.sqlite --data0 D:\工作目录\UI产物\data_0.big `
  --registry D:\工作目录\UI产物\custom_rosters.json `
  --imports D:\FO3ID\server\gamedata\player-imports.json `
  --portraits D:\工作目录\UI产物\assets\players --output D:\工作目录\完整产物
```

`check.py --full` 校验双端 UI 库相等、原生身份存在及新增记录回执、六语言姓名、头像、Lua 路由、所有登记的模型与骨骼/权重/索引/有限数值。来源或 checker 任一哈希改变，旧校验证书不能继续使用。新增保留选择器没有完整模型回执时直接拒绝。

正式发布继续使用共同发布锁、最新父层的全部 guards/receipt policies、当前文件备份及并发检查。游戏由用户正常退出；修改 UI SQLite 需要停受管服务并取本次实时资产快照。发布后在正式文件上再次 `--full`，把正式路径的 `player-import-validation.json` 纳入同一新子层。不要把工作产物路径的头像回执当成正式文件证明。`play-local.bat` 的独立玩家导入检查行必须保留。

```powershell
.venv\Scripts\python.exe -B tools\player_import\check.py --full
```

## 验收和经验记录

静态/结构/加解密/接口通过不等于实机通过。至少确认首页切换带球、近景、远景 LOD 和比赛加载/动画。没有实机证据的球员继续标 PENDING，不因一个贝林通过就标全员通过。不要用真实卡、余额或库存做自动测试。

当前已修资源保留贝林原有外貌和带球人工通过记录。其它人的原生验证单独记录。已存在的 Phil Neville、Nicky Butt 两张卡头像源缺失会使用客户端默认图；这是明确登记的旧缺项，不允许后续新增球员沿用该例外。Pogba 的一个历史模板继承值同样按明确名单保留，不作为 FC 星数导入规则。

这套规则拦截本次已知的漏库、错路由、错单位和不兼容资源；不能代替新资源的原生场景验收。故障证据、修复范围、失败样本和回归命令同时追加到 `docs/工程经验与修改边界.txt`，历史发行回执不改。
