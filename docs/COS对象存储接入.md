# COS 对象存储接入

> 把图片存到腾讯云 COS，减轻服务器系统盘压力。
> 已内置"本地/COS"双模式，改配置即可切换，无需改代码。

---

## 一、什么时候该用 COS

| 场景 | 推荐存储 |
|---|---|
| 单校小规模、图片不多 | 本地存储够用 (`STORAGE_TYPE=local`) |
| 长期使用、图片累积多 | **切 COS** (`STORAGE_TYPE=cos`)，系统盘永不满 |
| 需要图片 CDN 加速 | COS 自带 CDN |

---

## 二、获取 COS 配置（4 个参数）

### 1. 创建 COS 桶

1. 登录 [腾讯云 COS 控制台](https://console.cloud.tencent.com/cos)
2. **存储桶列表 → 创建存储桶**
   - 名称：自定义（如 `exam-grading-1250000000`，会带 APPID 后缀）
   - 地域：选离服务器近的（如 `ap-guangzhou` / `ap-beijing`）
   - 访问权限：**公有读私有写**（图片需要前端能访问）
3. 创建完成，记下：
   - **Bucket 名**（含 APPID）：`exam-grading-1250000000`
   - **地域**：`ap-guangzhou`

### 2. 获取 API 密钥

1. [API 密钥管理](https://console.cloud.tencent.com/cam/capi)
2. **新建密钥**，记下：
   - **SecretId**
   - **SecretKey**

⚠️ SecretKey 是敏感信息，**只填到服务器 `.env.prod`，不要提交到 Git**。

---

## 三、切换到 COS（在服务器操作）

### 1. 编辑配置

```bash
cd ~/exam-grading
nano .env.prod
```

找到存储部分，改成：

```bash
STORAGE_TYPE=cos
COS_SECRET_ID=你的SecretId
COS_SECRET_KEY=你的SecretKey
COS_REGION=ap-guangzhou            # 你的桶所在地域
COS_BUCKET=exam-grading-1250000000  # 你的桶名(含APPID)
```

保存（`Ctrl+O` → 回车 → `Ctrl+X`）。

### 2. 重启服务生效

```bash
# 用运维菜单（推荐）
bash deploy/menu.sh
# 选 4) 重启服务

# 或命令行
cd ~/exam-grading
sudo docker compose -f docker-compose.prod.yml restart
```

### 3. 验证

```bash
# 看日志确认 COS 初始化成功
sudo docker compose -f docker-compose.prod.yml logs backend --tail=20 | grep COS
# 应看到: COS 客户端已初始化: bucket=xxx region=xxx
```

然后上传一张答题卡，到腾讯云 COS 控制台看是否出现新文件。

---

## 四、工作原理

```
上传答题卡
  └─ scan_service.save_upload()
       └─ storage.save_bytes()  ─┬─ local: 写本地 storage/uploads/
                                 └─ cos:   传到 COS

判分读图
  └─ grading_dispatcher
       └─ storage.read_image()  ─┬─ local: 从本地读
                                 └─ cos:   从 COS 下载

前端看图 (/api/images/{id}/{kind})
  └─ get_image()
       ├─ local: FileResponse 直接返回文件
       └─ cos:   302 重定向到 COS 公网 URL（不占服务器带宽）
```

**核心**：业务层只调 `storage.save/read`，不关心数据存哪。`STORAGE_TYPE` 一改，自动切换。

---

## 五、费用估算（腾讯云 COS）

| 项目 | 单价 | 你的场景（单校小规模） |
|---|---|---|
| 存储 | ¥0.1/GB/月 | 100GB ≈ ¥10/月 |
| 上传请求 | 几乎免费 | 忽略不计 |
| 下载流量 | ¥0.5/GB | 仅看图时产生，量很小 |

**预计每月 ¥10-15**，比扩容系统盘划算得多。

---

## 六、常见问题

### Q: 切换 COS 后，之前本地存的图片怎么办？
之前的图片路径还是 `storage/uploads/xxx`，COS 里没有这些文件，访问会 404。
两个选择：
- **不管**：旧判分记录看不到图了，但数据还在。新上传的都走 COS。
- **迁移**：把本地 `storage/uploads/` 和 `storage/processed/` 的文件传到 COS（用 COSCMD 工具批量上传）。

### Q: COS 初始化报错？
```bash
# 看具体错误
sudo docker compose -f docker-compose.prod.yml logs backend | grep -i error
```
常见原因：
- SecretId/Key 填错
- Bucket 名没带 APPID 后缀
- 地域(region)填错

### Q: 想切回本地存储？
`.env.prod` 改回 `STORAGE_TYPE=local`，重启服务即可。COS 里的文件不受影响。

---

## 七、迁移已有图片到 COS（可选）

如果要把服务器上已有的图片传到 COS：

```bash
# 装 COSCMD 工具
pip install coscmd

# 配置（用你的 COS 参数）
coscmd config -a <SecretId> -s <SecretKey> -b <Bucket> -r <Region>

# 批量上传 storage 目录
cd ~/exam-grading
coscmd upload -r storage/ storage/
```

上传后，COS 里就有了和本地相同 key 的文件，切换 COS 模式后历史图片也能访问。
