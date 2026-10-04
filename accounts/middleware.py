# -*- coding: utf-8 -*-
"""安全中间件：校验 /api/fitness/ 的 owner 参数。

背景（2026-09-24 发现）：
  owner 会被直接拼进 DuckDB SQL 字符串（`WHERE w.owner = '{owner}'`），
  属读侧 SQL 注入面。2026-08-06 有外网扫描器把 SQLi/JNDI/反序列化 payload
  当 owner 写进了库（21 条空 workout + 1 条脏绑定）。

做法：
  owner 是「用户身份」参数，必须是干净的短标识符 —— 非法值**在进业务代码之前**直接 400，
  既不进 SQL，也不会被写成新用户。规则与小程序前端过滤保持一致。

范围（P0）：
  只校验 owner。⚠️ wechat create/bind 的 username 校验属 P1，尚未开启
  （要开只需把 _payload_names() 里的 'username' 也纳入校验）。
"""
import json
import logging
import re

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# 允许：字母 / 数字 / 下划线 / 中文 / 连字符，长度 1–20
SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9_\u4e00-\u9fa5-]{1,20}$')
GUARDED_PREFIX = '/api/fitness/'


def _payload_names(request):
    """POST/PUT/PATCH 的 body 里需要校验的字段名。

    P0：owner（会被拼进 SQL，注入面 + 垃圾用户来源）
    P1（2026-09-24 开启）：username（wechat create/bind 用，无校验就能造垃圾用户）
    ⚠️ 不要加 openid：真实 openid 长 28 位且字符集不同（o9bFo3d…），会被规则误杀。
    """
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
            if request.method in ('POST', 'PUT', 'PATCH'):
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
