# 记忆系统架构设计

> 用于面试的完整技术方案说明

---

## 一、架构总览

Agent 平台的记忆系统采用**三层分离**架构，每层各司其职，独立演进。

```
┌──────────────────────────────────────────────────────────┐
│                    Working Memory                         │
│              （工作记忆 / 运行时上下文管理）                │
│                                                          │
│  功能：在 token 预算内，组装最优的 LLM 上下文              │
│  存储：局部变量（函数内 messages 列表）                    │
│  生命周期：单个 HTTP 请求                                 │
│  对应文件：memory/manager.py                              │
├──────────────────────────────────────────────────────────┤
│                    Episodic Memory                        │
│              （情景记忆 / 关键信息提取）                   │
│                                                          │
│  功能：从对话中提取关键事实，按重要性排序，快速检索          │
│  存储：MySQL memory_episodes 表                           │
│  生命周期：永久                                           │
│  对应文件：memory/episodic.py                             │
├──────────────────────────────────────────────────────────┤
│                    Semantic Memory                        │
│              （语义记忆 / 向量相似度检索）                  │
│                                                          │
│  功能：用向量嵌入实现语义级匹配，不依赖关键词                │
│  存储：MySQL memory_semantic 表（BLOB 存向量）             │
│  生命周期：永久                                           │
│  对应文件：memory/semantic.py                             │
├──────────────────────────────────────────────────────────┤
│                    Conversation                           │
│              （完整会话记录 / 原始数据持久化）              │
│                                                          │
│  功能：保存每条原始消息，不改不删，作为记忆的"原料仓库"     │
│  存储：MySQL conversations + conversation_messages 表     │
│  生命周期：永久                                           │
│  对应文件：conversation/service.py                        │
└──────────────────────────────────────────────────────────┘
```

---

## 二、各层详解

### 2.1 Working Memory（工作记忆）

**职责**：决定 LLM 当前能看到什么历史内容。

**处理流水线：**

```
Conversation 原始消息（MySQL 拉取）
  │
  │  MemoryManager.build_context()
  │
  ├─ Level 0a: Episodic 注入
  │    检索最近 3 条重要事实 → 拼成 system message
  │
  ├─ Level 0b: Semantic 注入（如有 query）
  │    query → embedding 向量化 → 余弦相似度匹配
  │    命中 >0.7 的作为补充记忆注入
  │
  ├─ Level 1: 单条截断
  │    单条消息超过 budget 50% 时，保留开头 20% + 结尾 80%
  │    中间插入 "内容过长已截断" 提示
  │
  ├─ Level 2: 滑动窗口
  │    从最新的消息开始往前保留，超出 budget 的剔除
  │
  └─ Level 3: 摘要压缩
       剔除的消息用 LLM 压缩成一句话摘要
       摘要也作为一个 system message 参与上下文
  │
  ▼
最终 messages → LLM invoke
```

**关键设计考量：**

```
为什么不用消息条数做窗口，而用 token 数？
  token 数才是 LLM 上下文的真实限制。20 条短消息可能只占 500 tokens，
  但 1 条长代码就可能占 4000 tokens。按条数截断要么浪费空间，要么不够用。
```

**限制和不足：**

```
- 每次请求重新计算（无法复用上次的摘要结果）
- 单机内存，不可共享
```

### 2.2 Episodic Memory（情景记忆）

**职责**：记住"用户说过什么重要的事"，跨会话保持关键上下文。

**存储结构：**

```sql
CREATE TABLE memory_episodes (
  id         INT AUTO_INCREMENT,
  agent_id   INT NOT NULL,          -- 每个 Agent 隔离
  session_id VARCHAR(100),          -- 来源会话
  content    TEXT NOT NULL,          -- 关键信息摘要
  type       VARCHAR(20),           -- fact / preference / decision
  importance INT DEFAULT 1,         -- 1-5，越提越高
  created_at DATETIME,
  PRIMARY KEY (id),
  INDEX (agent_id, importance)
);
```

**提取触发：**

```
LLM 回复后 → extract_and_save()
  ├── 调 LLM 分析对话内容
  │   只提取跨会话有价值的信息：
  │   ✓ fact: 技术栈、项目信息、背景
  │   ✓ preference: 用户偏好、习惯
  │   ✓ decision: 技术决策、结论
  │   ✗ 跳过：打招呼、推理过程、通用知识
  │
  ├── 存入 memory_episodes
  │   去重：字符重叠度 ≥ 0.5 视为重复 → importance +1
  │
  └── 同时存入 memory_semantic（带向量）
```

**检索方式：**

```sql
SELECT * FROM memory_episodes
WHERE agent_id = ?
ORDER BY importance DESC, created_at DESC
LIMIT 3;
```

### 2.3 Semantic Memory（语义记忆）

**职责**：解决"关键词匹配不到但意思相关"的问题。和 Episodic 互补。

```python
# 调 SiliconFlow 的 BGE-large-zh-v1.5 API
# 不需要本地部署向量模型，不需要 GPU
# 复用 AsyncOpenAI 客户端，全局单例，带 2s 超时

async def search_memories(agent_id, query, top_k=3, min_score=0.7):
    query_vec = await embed_text(query)      # 调 API 向量化
    memories = load_all(agent_id)            # 全量加载（千级以下）
    scored = cosine_similarity(query_vec, memories)
    return scored[score > min_score][:top_k]
```

**去重也基于余弦相似度**（≥0.85 视为重复），比 Episodic 的字符级匹配更准："在用 Spring Boot"和"使用 Spring Boot 框架"意思相同、用词不同，字符匹配不到但向量能匹配到。

### 2.4 Conversation（会话记录）

**职责**：完整保存原始对话，不改不删。是 Working Memory 的数据源，也是 Episodic/Semantic 的分析原料。

```sql
-- 会话元数据
conversations (session_id, agent_id, name, message_count)

-- 消息明细
conversation_messages (conversation_id, role, content, msg_index)
```

---

## 三、数据流全景

```
写入流（用户发消息 → 回复完成）
───────────────────────────────────────────────────

用户发消息
  │
  ├── 1. ConversationService.add_message()
  │     MySQL 永久存储原始消息
  │
  ├── 2. MemoryManager.build_context()
  │     ├── 拉取历史（Conversation）
  │     ├── 检索记忆（Episodic + Semantic）
  │     ├── 截断 + 窗口 + 摘要
  │     └── 组装最终上下文
  │
  ├── 3. LLM invoke → 回复
  │
  └── 4. extract_and_save()  ← 异步，不阻塞用户
        ├── LLM 提取关键信息
        ├── memory_episodes（结构化）
        └── memory_semantic（向量化）


读取流（用户发新消息 → 记忆注入）
───────────────────────────────────────────────────

用户："之前说用什么框架？"
  │
  ├── Episodic: SELECT WHERE agent_id=1 ORDER BY importance DESC LIMIT 3
  │   → "用户在用 Spring Boot" (importance=3)
  │
  ├── Semantic: embedding("用什么框架") → 余弦搜索
  │   → "用户在用 Spring Boot 3.2" (score: 0.92)
  │
  └── 合并注入 → "关于用户的记忆: ..."
      → LLM 看到上下文，准确回复
```

---

## 四、企业级优化方向

### 方向 1：异步化 Semantic 检索

```
当前：semantic 检索 → LLM 推理           ← 串行，等 embedding
改进：LLM 推理（同时后台异步 semantic）
      semantic 结果不用于本次回复，缓存供下一次使用
      → 消除 embedding API 延迟对用户体验的影响
```

### 方向 2：记忆融合（Memory Consolidation）

当前存在相同事实的不同表述：

```
会话 1: "用户在用 Spring Boot"
会话 2: "用户用的是 Spring Boot 3.2"
```

改进：定时后台任务，对相似记忆（余弦 ≥0.85）自动合并为一条更完整的表述，保留最高的 importance。

### 方向 3：时间衰减 + 遗忘曲线

```
当前：重要性只能 +1，不会降
改进：长时间未提及的记忆自动衰减 importance
  importance = base * e^(-λt)
  λ 半衰期可配置（如 30 天）
  衰减到 0 自动归档
```

这符合人类的记忆规律——不反复提起的事会逐渐忘记。

### 方向 4：记忆管理界面

当前 memory_episodes 和 memory_semantic 对用户不可见、不可编辑。企业级要求：

```
- 后台页面展示所有记忆
- 支持手动添加、编辑、删除记忆
- 支持标记"固定"（always inject）
- 查看记忆来源会话（跳转）
- 按 Agent 筛选、按类型筛选
```

### 方向 5：多级缓存

```
当前：每次 build_context 都查 MySQL
改进：
  L1: Redis 缓存最近高频记忆（TTL 1h）
  L2: MySQL 全量数据
  权衡：缓存一致性维护成本 vs MySQL 查询 2ms 的收益
```

对于当前规模 MySQL 直查已经够用。数据量上千万后考虑。

### 方向 6：向量检索规模化

```
当前：全量加载 + Python 余弦计算（百万级以下适用）
瓶颈：1 万条记忆 → 全量加载 ~100ms + 余弦计算 ~50ms
      10 万条 → ~1s+，不可接受
改进：
  1. MySQL 8.0 VECTOR 索引（原生支持，无需额外组件）
  2. 或接入 Chroma/Milvus 专用向量库
```

### 方向 7：长对话的渐进式摘要

```
当前：摘要只做一次，丢掉的消息再也查不到
改进：分层摘要树
    
  Round 1-10  → 摘要 A
  Round 11-20 → 摘要 B
  Round 21-30 → 摘要 C
  A + B + C   → 全局摘要 D
  
  需要时，用户可"展开"某段摘要查看原始消息
  类似 git 的 squash 和 reflog
```

---

## 五、面试话术

### Q: 为什么用三层分离架构？

> 单一存储无法同时满足三个需求：
> 1. 完整的原始记录（Conversation）—— 用于审计、追溯、搜索
> 2. 快速的关键信息获取（Episodic）—— 用于高频场景，ms 级响应
> 3. 精准的语义匹配（Semantic）—— 用于复杂查询，不受关键词限制
>
> 三层分工后，Conversation 只管存、Memory 只管查，互不干扰，各自可以独立优化。

### Q: Episodic 和 Semantic 有什么区别？为什么不合并？

> Episodic 是"结构化检索"—— 按重要性和时间排序，取最近最重要的几条。快、简单、可靠，适合高频刚需场景。
>
> Semantic 是"语义检索"—— 把问题和记忆都转成向量，算余弦相似度。准、不怕被淹没，适合深度查询场景。
>
> 两者互补：Episodic 保证高频记忆不丢，Semantic 保证相关记忆能找。不合并是因为检索方式完全不同，合并了会互相拖累。

### Q: 为什么要向量化，不用关键词匹配？

> 用户不会用精确的"记忆中的关键词"来提问。他说"那个绿色 logo 的云服务"，你要能匹配到"在用阿里云"。关键词匹配做不到，语义匹配可以。这就是引入向量的原因。

### Q: 为什么不用向量数据库？

> 当前数据量（千级）全量加载 + Python 余弦计算只要几十毫秒，引入向量数据库增加运维复杂度但收益为零。架构上预留了升级路径：MySQL 8.0 VECTOR 索引或 Chroma，等数据量到了万级以上再考虑。

### Q: 去重怎么做的？

> 两套去重方案：
> - Episodic：字符重叠度（简单粗暴，对 30 字短文本够用）
> - Semantic：余弦相似度 ≥0.85（调一次 embedding API，比字符级更准）
>
> 命中重复时不插入新记录，而是给旧记录的 importance +1。这样用户反复提同一件事时，这条记忆越变越重要，不会被新记忆挤掉。

### Q: 这个方案的最大瓶颈是什么？

> Embedding API 的延迟。每次 Semantic 检索都要调一次 SiliconFlow API（~100-200ms），虽然加了超时和 client 复用，但网络延迟没法消除。
>
> 解决方向：将 Semantic 检索异步化，不阻塞主推理链路。本次查询结果缓存供下次使用。

### Q: 如果多个 Agent 之间需要共享记忆怎么设计？

> 当前按 agent_id 隔离，天然支持 Agent 级别的权限控制。如果需要共享，可以加一张全局记忆表或共享标签机制——记忆可标记为"私有的"或"共享的"，检索时按权限范围过滤。
