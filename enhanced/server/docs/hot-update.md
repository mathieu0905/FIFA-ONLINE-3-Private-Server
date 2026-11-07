# FO3 业务热更新，ABI 1

首次引导接入前，正式运行进程仍保持旧行为。首次接入只能在用户结束游玩后正常重启一次；之后发布兼容的业务处理函数不重启HTTPS、管理页或messenger。不得退出游戏、重启服务来“完成热更新”。

当前能力：精确HTTP路径的商城、道具、背包、活动处理函数；已有旧实现保持为默认。代码需改写为下面的函数形式，普通Python文件覆盖不会自动热加载，后台市场worker/对象方法/闭包也不会自动更新。不支持新连接协议、TCP消息核心、比赛、经理会话、数据库结构或客户端BIG/模型/语言资源。

```python
def event_list(host, query, body):
    # host为当前HTTP模块，沿用当前STATE_LOCK与原子存档函数。
    # 真实付费/发卡事务必须保留全部校验、幂等及一次性保存语义。
    return host._json({"events": []})
```

顶层只允许无装饰器、无注解、无默认参数的函数定义和文档字符串。禁止模块导入时注册路由/写存档/启动线程；需要的普通库可在函数内部导入。这是受信任维护者发布代码的机制，不是Python沙箱。函数签名必须为 `(host, query, body)`，不允许通过热包改写host连接、类、全局变量或启动/停止后台任务。

发布前须用临时数据完成该业务自己的契约/事务/幂等回归；框架只验证加载和切换机制，不保证业务代码正确。不得使用真实余额/卡进行测试。兼容响应类型与原接口契约必须保持。若业务在运行中抛异常，沿用原HTTP错误处理，绝不自动用旧函数重放，以免重复扣费或发卡。

正式服务目录执行：

```powershell
.venv\Scripts\python.exe -B hot_update_control.py
.venv\Scripts\python.exe -B hot_update_publish.py --source D:\path\reviewed-business.py --revision event_001 --expected-revision bootstrap --route /events=event_list
.venv\Scripts\python.exe -B hot_update_control.py
```

只有状态中的revision变为event_001且error为空才算运行时已激活。发布成功不等于激活成功。每次发布都沿用共同双锁、实际最新父层、全部guards和receipt policies，注册不可变business.py、新子层及备份，play最后切换，active.json最后原子替换；不改state/shop。运行时只读取这一版的已绑定代码/manifest/receipt，编译在STATE_LOCK外，切换在锁内完成。发布锁存在时加载器等待，不读取半套发行文件。加载失败保留旧映射；修正代码必须新建revision重新发布。

```powershell
# 退回一个历史业务版本，或撤下全部热路由恢复宿主原实现；都不重启服务。
.venv\Scripts\python.exe -B hot_update_control.py --rollback event_001
.venv\Scripts\python.exe -B hot_update_control.py --disable
```

回退仅切换业务函数，不回退存档、不撤销已完成交易。状态中的error应为空；路径不存在时不会自动卸载当前版本。不可变历史代码/发布凭据不可删改。未来更换宿主API或撤销已售商品兼容性前，必须评估现存热包并迁移或停用；ABI需变化时不得宣称为兼容热更新。

验证：工作目录test_hot_update.py，包括坏哈希/语法/回执、核心路径拒绝、请求边界并发、旧函数引用、已存在socket、冷启动恢复、回退及发布事务故障回滚。未自动进行游戏GUI或比赛验证。


## ABI 2 动态道具路径（随 draw-first 组合安装加载）

ABI 2 保留 ABI 1 固定业务路由，并增加三个受限模板：`/item/{item_id}/use`、`/item/depottoitem/{item_id}`、`/bag/{bag_id}/unpack`。仅匹配原生已有的完整路径，参数限 `\w+`；不接受任意正则、核心路径、通配符或路径后缀。业务函数从只读 `host.hot_path_params` 读取捕获参数，其余属性读取宿主，禁止写宿主属性。精确路由优先，请求捕获彼此隔离，换代保留已取出的处理函数。

该扩展改变宿主调度器，只能在游戏自然结束后的组合安装中加载，不能由 ABI 1 热包重跑 install hooks 或改写运行中的全局对象。实际 control 返回 abi=2 之前，不发布含模板的热包。旧业务热包描述符 abi=1 仍按精确路径恢复；新版发布工具产生 abi=2 描述符。

draw-first 同一组合安装注册新随机 SKU 和原生风格图标，冻结具体 SPID、权重与强化概率，保留已售自选包和旧礼包定义。开包适配器仅委托已注册的原生事务引擎，不创建第二套服务、不重放失败交易、不覆盖真实存档。回归见 D:\fifaol3\draw-first\test.py（36种动态开包/重放、五条连锁购买/重放/篡改报价拒绝）和 hot-v2/dynamic-tests.json、hot-v2/tests.json；实机显示及比赛另行记录。
