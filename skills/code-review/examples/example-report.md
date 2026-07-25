## 审查示例

### 输入代码
```python
def get_user(user_id):
    db = get_db()
    users = db.query("SELECT * FROM users")
    for u in users:
        if u['id'] == user_id:
            return u
```

### 预期输出
```
## 文件：user_service.py

### 🔴 严重（2）
1. SQL 未使用参数化查询，存在注入风险 → 改用 `WHERE id = ?`
2. 全表扫描后内存过滤，大数据量时 OOM → 使用 `WHERE id = ?` 由数据库过滤

### 🟡 建议（1）
1. 函数未处理 user_id 为 None 的情况 → 添加参数校验

### ✅ 值得肯定
- 函数命名清晰，单一职责
```
