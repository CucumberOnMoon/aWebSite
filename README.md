# aWebSite · 推拉腿王者

个人健身训练记录系统：**微信小程序**（前端）+ **Django REST 后端**（DuckDB 存训练数据）。

- 小程序 AppID：`wx06ccc7d635a3bdc0`
- 线上后端：香港 VPS（`103.30.77.149`），gunicorn + nginx
- 训练数据：DuckDB `/root/data/workout.db`

## 仓库结构

```
accounts/            Django app：用户、训练记录、API、OCR 等
web_project/         Django 工程配置（settings / urls / wsgi）
templates/ static/   后端页面与静态资源
miniprogram/         微信小程序（前端，以此为准）
manage.py requirements.txt .env.example
```

## 分支

**只有 `main`**（2026-10-04 起）。此前的 `master` 已合并进 `main` 并删除。

分工约定：**后端以 VPS 的工作副本为准，前端以小程序的开发副本为准**（两边各自提交推送到 `main`）。

## 资产与备份

动作演示 GIF 等大二进制**不入库**（见 `.gitignore`）：

```
venv/                         Python 虚拟环境
staticfiles/                  collectstatic 产物
static/images/                后端动作 GIF（2146 个，约 204 MB）
miniprogram/images/ex-demos/  小程序动作 GIF（1079 个，约 103 MB）
```

这些资产**只在 VPS 上**，丢失不可再生，因此另做离线备份。

### 备份位置

```
崇明 NAS：/share/CACHEDEV3_DATA/aWebSite-backup/
├── MANIFEST.txt                  备份清单（时间/来源/恢复方法）
├── assets/
│   ├── static-images/            ← static/images/
│   └── miniprogram-ex-demos/     ← miniprogram/images/ex-demos/
└── db/
    ├── db.sqlite3                Django 运行库（用户/会话）
    ├── test_db.sqlite3           测试库
    ├── workout.db                健身主库（DuckDB）
    ├── social_security.db        社保库（DuckDB）
    ├── table_tennis.db           乒乓参赛库（DuckDB）
    ├── requirements.txt .env.example
    └── SHA256SUMS                校验值
```

- 备份为**手动触发**，脚本在 VPS 上：`/root/aWebSite-backup-to-nas.sh`
- 数据库取的是**一致性快照**（SQLite 用 `sqlite3` 的 backup API；DuckDB 先 `CHECKPOINT` 再复制），不是裸 `cp`
- NAS 凭据不入库（另存于 VPS 的密钥文件）

### 恢复

```bash
# 资产
rsync -a <NAS>/aWebSite-backup/assets/static-images/        static/images/
rsync -a <NAS>/aWebSite-backup/assets/miniprogram-ex-demos/ miniprogram/images/ex-demos/

# 数据库（先停服务，避免写入冲突）
sudo systemctl stop awebsite.service
cp <NAS>/aWebSite-backup/db/workout.db /root/data/workout.db
cp <NAS>/aWebSite-backup/db/db.sqlite3 ./
sudo systemctl start awebsite.service
```

## 本地运行（后端）

```bash
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 按需填
python manage.py migrate
python manage.py runserver
```
