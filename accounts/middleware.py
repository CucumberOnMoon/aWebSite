# -*- coding: utf-8 -*-
"""安全中间件：校验 /api/fitness/ 的 owner 参数 + 按 openid 强制身份。

背景（2026-09-24 发现）：
  owner 会被直接拼进 DuckDB SQL 字符串（`WHERE w.owner = '{owner}'`），
  属读侧 SQL 注入面。2026-08-06 有外网扫描器把 SQLi/JNDI/反序列化 payload
  当 owner 写进了库（21 条空 workout + 1 条脏绑定）。

做法：
  owner 是「用户身份」参数，必须是干净的短标识符 —— 非法值**在进业务代码之前**直接 400，
  既不进 SQL，也不会被写成新用户。规则与小程序前端过滤保持一致。

身份（2026-10-30 新增）：
  写操作（POST/PUT/PATCH/DELETE）不再信任前端自报的 owner。
  小程序每次请求带 `X-Openid`，中间件查 wechat_binds 解析成 username，
  注入 request.identity_owner；accounts/api._owner() 优先采用它。
  → 谁登录就写谁名下，冒充不了别人。
  读操作（GET）不覆盖 —— 小程序需要切换查看他人数据。

范围（P0）：
  只校验 owner / username。
"""
import json
import logging
import os
import re
import shutil
import subprocess
import time

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# 允许：字母 / 数字 / 下划线 / 中文 / 连字符，长度 1–20
SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9_\u4e00-\u9fa5-]{1,20}$')
GUARDED_PREFIX = '/api/fitness/'
WRITE_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')

# ── 身份解析：openid → username ────────────────────────────────────────
_DB_PATH = os.environ.get('WORKOUT_DB_PATH', '/root/data/workout.db')
_DUCKDB = shutil.which('duckdb') or '/usr/local/bin/duckdb'
# 🚨 2026-10-30：只读查询必须带 -readonly + 走同一个跨进程闸，
#    否则并发时会撞 DuckDB 独占锁 → openid 解析失败 → 用户被当成"未绑定"。
#    闸文件与 accounts/views.py 的 _DB_GATE_PATH 必须一致。
_DB_GATE_PATH = '/root/data/workout.db.gate'
_IDENT_TTL = 60
_ident_cache = {}          # openid -> (username, ts)


def _resolve_openid(openid):
    """openid → username（查 wechat_binds），60s 内存缓存。查不到返回 ''。"""
    now = time.time()
    hit = _ident_cache.get(openid)
    if hit and now - hit[1] < _IDENT_TTL:
        return hit[0]

    sql = ("SELECT username FROM wechat_binds WHERE openid = '"
           + openid.replace("'", "''") + "'")
    name = ''
    try:
        import fcntl
        with open(_DB_GATE_PATH, 'a') as _gate:
            fcntl.flock(_gate, fcntl.LOCK_SH)
            try:
                r = subprocess.run(
                    [_DUCKDB, '-readonly', _DB_PATH, '-csv', '-noheader', '-c', sql],
                    capture_output=True, text=True, timeout=10,
                )
            finally:
                fcntl.flock(_gate, fcntl.LOCK_UN)
        if r.returncode == 0 and (r.stdout or '').strip():
            # ⚠️ duckdb -csv 给非 ASCII 值加双引号（"夯嘚嫑嫑啲"）→ 必须剥掉，
            #    否则 SAFE_NAME_RE 校验不过，所有写操作的身份都会被拒。
            name = r.stdout.strip().splitlines()[0].strip().strip('"')
        elif r.returncode != 0:
            logger.warning('openid 解析 SQL 失败: %s', (r.stderr or '')[:200])
    except Exception as e:                                  # noqa: BLE001
        logger.warning('openid 解析异常: %s', e)

    if name and not SAFE_NAME_RE.match(name):
        logger.warning('wechat_binds 里存了非法 username: %r（openid %s…）', name, openid[:8])
        name = ''

    _ident_cache[openid] = (name, now)
    return name


def _payload_names(request):
    """POST/PUT/PATCH 的 body 里需要校验的字段名。

    P0：owner（会被拼进 SQL，注入面 + 垃圾用户来源）
    P1（2026-09-24 开启）：username（wechat create/bind 用，无校验就能造垃圾用户）
    ⚠️ 不要加 openid：真实 openid 长 28 位且字符集不同（o9bFo3d…），会被规则误杀。
    ⚠️ 身份已由 openid 覆盖时不再校验 owner —— 前端传什么都会被忽略。
    """
    if getattr(request, 'identity_owner', None):
        return ('username',)
    return ('owner', 'username')


def _body_value(request, names):
    """从 body 取待校验值 → (字段名, 值)：JSON 优先（小程序/QQ bot 都发 JSON），否则表单。"""
    ctype = (request.content_type or '').lower()
    if 'json' in ctype:
        try:
            data = json.loads(request.body or b'{}')
        except (ValueError, TypeError):
            return None, None
        if isinstance(data, dict):
            for key in names:
                val = data.get(key)
                if val not in (None, ''):
                    return key, str(val)
        return None, None
    for key in names:
        val = request.POST.get(key)
        if val:
            return key, str(val)
    return None, None


class OwnerValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(GUARDED_PREFIX):
            # 1) 身份：写操作按 openid 强制归属（读操作不动）
            if request.method in WRITE_METHODS:
                openid = (request.META.get('HTTP_X_OPENID') or '').strip()
                if openid:
                    username = _resolve_openid(openid)
                    if username:
                        request.identity_owner = username
                        logger.info(
                            '身份覆盖 %s %s → owner=%s（openid %s…）',
                            request.method, request.path, username, openid[:8],
                        )
                    else:
                        logger.warning(
                            '未知 openid，未覆盖：%s %s（openid %s…，前端自报 owner 仍会被校验）',
                            request.method, request.path, openid[:8],
                        )

            # 2) 校验：非法 owner/username 在进业务代码之前拦掉
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                field, raw = _body_value(request, _payload_names(request))
            else:
                field, raw = 'owner', request.GET.get('owner')
            if raw is not None:
                cleaned = str(raw).strip()
                if not SAFE_NAME_RE.match(cleaned):
                    logger.warning(
                        '拒绝非法 %s：%r（%s %s，来源 %s）',
                        field, cleaned[:60], request.method, request.path,
                        request.META.get('REMOTE_ADDR'),
                    )
                    return JsonResponse(
                        {'error': f'{field} 参数不合法：只允许字母/数字/下划线/中文/连字符，长度 1-20'},
                        status=400,
                    )
        return self.get_response(request)
