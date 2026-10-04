"""
DuckDB Fitness REST API — browsable with DRF.

Endpoints:
  GET/POST  /api/fitness/workouts/          — list / create workouts
  GET       /api/fitness/workouts/<id>/     — workout detail with sets
  PATCH     /api/fitness/workouts/<id>/     — update duration / note
  GET       /api/fitness/workouts/last/     — last workout with sets
  GET       /api/fitness/exercises/         — list exercises
  POST      /api/fitness/sets/              — add sets (bulk)
  GET       /api/fitness/stats/             — aggregated stats
  GET/POST  /api/fitness/cycle/             — get current / create cycle
  PATCH     /api/fitness/cycle/<id>/        — update cycle entry
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from .views import _run_workout_query, _parse_duckdb_table

import datetime
import logging
import math
import re

logger = logging.getLogger(__name__)

# owner 必须是干净的短标识符（与 accounts/middleware.py 同一套规则）
SAFE_OWNER_RE = re.compile(r'^[A-Za-z0-9_\u4e00-\u9fa5-]{1,20}$')

# ── helpers ──────────────────────────────────────────────────────────

def _owner(request):
    """Get owner: from body for POST/PATCH, else from query param or fallback.

    第二层防线（第一层是 accounts/middleware.OwnerValidationMiddleware）：
    非法 owner 不返回原值 —— 返回一个合法字符集内、绝不可能存在的哨兵，
    这样即便中间件被绕过，脏值也进不了 SQL、也不会落到其他用户名下。
    """
    if request.method in ('POST', 'PATCH') and request.data.get('owner'):
        raw = str(request.data['owner']).strip()
    else:
        raw = str(request.query_params.get('owner') or 'howard').strip()
    if not SAFE_OWNER_RE.match(raw):
        logger.warning('_owner() 兜底拦截非法 owner: %r', raw[:60])
        return '__invalid_owner__'
    return raw

BODY_WEIGHT = 75
ASSISTED = {"助力引体向上", "双杠臂屈伸(助力)"}


def _adjust(row):
    """Same assisted-weight adjustment as the template view."""
    if row.get('name') in ASSISTED:
        if 'max_weight' in row and row['max_weight']:
            row['max_weight'] = round(BODY_WEIGHT - row['max_weight'], 1)
        if 'avg_weight' in row and row['avg_weight']:
            row['avg_weight'] = round(BODY_WEIGHT - row['avg_weight'], 1)
        if 'weight_kg' in row and row['weight_kg']:
            row['weight_kg'] = round(BODY_WEIGHT - row['weight_kg'], 1)
    if row.get('exercise') in ASSISTED and 'weight_kg' in row and row['weight_kg']:
        row['weight_kg'] = round(BODY_WEIGHT - row['weight_kg'], 1)
    return row


def _run_sql(sql):
    raw = _run_workout_query(sql)
    if raw is None:
        return None
    return _parse_duckdb_table(raw)


# ── workouts ─────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def workout_list(request):
    """List all workouts, or create a new one."""
    if request.method == 'GET':
        limit = request.query_params.get('limit', 50)
        sql = f"""\
            SELECT w.id, w.date, w.type, w.duration_min, w.note,
                   COUNT(s.id) as sets,
                   COALESCE(ROUND(SUM(s.weight_kg * s.reps)), 0) as total_volume
            FROM workouts w
            LEFT JOIN sets s ON w.id = s.workout_id
            WHERE w.owner = '{_owner(request)}'
            GROUP BY w.id, w.date, w.type, w.duration_min, w.note
            ORDER BY w.date DESC
            LIMIT {limit}
        """
        data = _run_sql(sql)
        if data is None:
            return Response({'error': '数据库查询失败'}, status=500)
        return Response(data)

    # POST — create workout
    date = request.data.get('date')
    wtype = request.data.get('type')
    duration = request.data.get('duration_min')
    note = request.data.get('note', '')

    if not date or not wtype:
        return Response({'error': 'date 和 type 必填'}, status=400)
    if wtype not in ('Push', 'Pull', 'Legs'):
        return Response({'error': 'type 必须是 Push/Pull/Legs'}, status=400)

    duration_sql = f", {duration}" if duration else ", NULL"
    note_sql = f", '{note.replace(chr(39), chr(39)+chr(39))}'" if note else ", NULL"
    sql = f"""\
        INSERT INTO workouts (id, date, type, duration_min, note, owner)
        VALUES (nextval('seq_workout_id'), '{date}', '{wtype}'
                {duration_sql}{note_sql}, '{_owner(request)}')
        RETURNING id
    """
    raw = _run_workout_query(sql)
    if not raw:
        return Response({'error': '创建失败'}, status=500)

    rows = _parse_duckdb_table(raw)
    new_id = rows[0]['id'] if rows else None
    return Response({'id': new_id, 'date': date, 'type': wtype}, status=201)


@api_view(['GET', 'PATCH'])
@permission_classes([AllowAny])
def workout_detail(request, pk):
    """Single workout with sets (GET), or update duration/note (PATCH)."""
    if request.method == 'GET':
        sql = f"SELECT * FROM workouts WHERE id = {pk} AND owner = '{_owner(request)}'"
        workout = _run_sql(sql)
        if not workout:
            return Response({'error': '未找到训练'}, status=404)

        data = workout[0]
        sets_sql = f"""\
            SELECT s.id, s.set_number, s.weight_kg, s.reps, s.rpe,
                   e.id as exercise_id, e.name as exercise, e.name_cn as exercise_cn, e.category
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.workout_id = {pk} AND s.owner = '{_owner(request)}'
            ORDER BY e.id, s.set_number
        """
        raw = _run_workout_query(sets_sql)
        data['sets'] = [_adjust(r) for r in (_parse_duckdb_table(raw) or [])] if raw else []
        return Response(data)

    # PATCH — update duration / note / summary
    updates = []
    if 'duration_min' in request.data:
        val = request.data['duration_min']
        updates.append(f"duration_min = {val}" if val is not None else "duration_min = NULL")
    if 'note' in request.data:
        n = request.data['note'].replace(chr(39), chr(39) + chr(39))
        updates.append(f"note = '{n}'" if n else "note = NULL")
    if 'summary' in request.data:
        s = request.data['summary'].replace(chr(39), chr(39) + chr(39))
        updates.append(f"summary = '{s}'" if s else "summary = NULL")

    if not updates:
        return Response({'error': '没有可更新的字段'}, status=400)

    sql = f"UPDATE workouts SET {', '.join(updates)} WHERE id = {pk} AND owner = '{_owner(request)}'"
    _run_workout_query(sql)
    return Response({'status': 'updated', 'id': pk})


@api_view(['GET'])
@permission_classes([AllowAny])
def workout_last(request):
    """Most recent workout with full set details. Optional ?offset=N for Nth most recent."""
    offset = int(request.query_params.get('offset', 0))
    sql = f"SELECT id, date, type, duration_min, note, summary FROM workouts WHERE owner = '{_owner(request)}' ORDER BY date DESC LIMIT 1 OFFSET {offset}"
    rows = _run_sql(sql)
    if not rows:
        return Response({'error': '没有更多训练记录'}, status=404)

    data = rows[0]
    pk = data['id']
    sets_sql = f"""\
        SELECT s.id, s.set_number, s.weight_kg, s.reps, s.rpe,
               e.id as exercise_id, e.name as exercise, e.name_cn as exercise_cn, e.category
        FROM sets s
        JOIN exercises e ON s.exercise_id = e.id
        WHERE s.workout_id = {pk} AND s.owner = '{_owner(request)}'
        ORDER BY e.id, s.set_number
    """
    raw = _run_workout_query(sets_sql)
    data['sets'] = [_adjust(r) for r in (_parse_duckdb_table(raw) or [])] if raw else []
    return Response(data)


# ── exercises ────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def exercise_list(request):
    """List all exercises, or create a new one."""
    if request.method == 'GET':
        data = _run_sql("SELECT * FROM exercises ORDER BY category, id")
        if data is None:
            return Response({'error': '查询失败'}, status=500)
        return Response(data)

    # POST — create exercise
    name = request.data.get('name')
    category = request.data.get('category')
    target_muscle = request.data.get('target_muscle', '')

    if not name or not category:
        return Response({'error': 'name 和 category 必填'}, status=400)
    if category not in ('Push', 'Pull', 'Legs'):
        return Response({'error': 'category 必须是 Push/Pull/Legs'}, status=400)

    safe_name = name.replace(chr(39), chr(39) + chr(39))
    safe_target = target_muscle.replace(chr(39), chr(39) + chr(39))
    sql = f"""
        INSERT INTO exercises (id, name, category, target_muscle)
        VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM exercises), '{safe_name}', '{category}', '{safe_target}')
        RETURNING id
    """
    raw = _run_workout_query(sql)
    if not raw:
        return Response({'error': '创建失败'}, status=500)

    rows = _parse_duckdb_table(raw)
    new_id = rows[0]['id'] if rows else None
    return Response({'id': new_id, 'name': name, 'category': category, 'target_muscle': target_muscle}, status=201)


# ── sets ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def set_create(request):
    """Add one or more sets to a workout.
    Accepts a single set or an array of sets.
    """
    if isinstance(request.data, list):
        items = request.data
    else:
        items = [request.data]

    results = []
    for item in items:
        workout_id = item.get('workout_id')
        exercise_id = item.get('exercise_id')
        set_number = item.get('set_number')
        weight = item.get('weight_kg')
        reps = item.get('reps')
        rpe = item.get('rpe')

        if not all([workout_id, exercise_id, set_number is not None]):
            return Response({'error': 'workout_id, exercise_id, set_number 必填'}, status=400)

        weight_sql = weight if weight is not None else "NULL"
        reps_sql = reps if reps is not None else "NULL"
        rpe_sql = f", {rpe}" if rpe is not None else ", NULL"

        sql = f"""\
            INSERT INTO sets (id, workout_id, exercise_id, set_number, weight_kg, reps, rpe, owner)
            VALUES (nextval('seq_set_id'), {workout_id}, {exercise_id}, {set_number},
                    {weight_sql}, {reps_sql}{rpe_sql}, '{_owner(request)}')
            RETURNING id
        """
        raw = _run_workout_query(sql)
        if raw:
            rows = _parse_duckdb_table(raw)
            results.append({'id': rows[0]['id']} if rows else {})
        else:
            results.append({'error': f'set {set_number} 添加失败'})

    return Response({'sets': results}, status=201)


# ── set history (force curve) ────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def set_history(request):
    """Return best set per training day for one exercise, or all."""
    ex_id = request.query_params.get('exercise_id')
    owner = _owner(request)

    where = f"s.owner = '{owner}'"
    if ex_id:
        where += f" AND s.exercise_id = {ex_id}"

    sql = f"""\
        SELECT exercise_id, name, category, weight_kg, reps, date FROM (
            SELECT e.id as exercise_id, e.name, e.category,
                   s.weight_kg, s.reps, w.date,
                   ROW_NUMBER() OVER (
                       PARTITION BY e.id, w.date
                       ORDER BY s.weight_kg DESC, s.reps DESC
                   ) as rn
            FROM sets s
            JOIN workouts w ON s.workout_id = w.id
            JOIN exercises e ON s.exercise_id = e.id
            WHERE {where}
        ) sub WHERE rn = 1
        ORDER BY date
    """
    rows = _run_sql(sql)
    if rows:
        rows = [_adjust(r) for r in rows]
    return Response(rows or [])


# ── stats ────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def stats_overview(request):
    """Aggregated stats: totals, per-category, per-exercise, progress."""
    # Total stats
    total_sql = f"""\
        SELECT COUNT(DISTINCT w.id) as total_workouts,
               COUNT(s.id) as total_sets,
               COALESCE(ROUND(SUM(s.weight_kg * s.reps)), 0) as total_volume,
               MIN(w.date) as first_date,
               MAX(w.date) as last_date
        FROM workouts w
        JOIN sets s ON w.id = s.workout_id
        WHERE w.owner = '{_owner(request)}'
    """
    totals = _run_sql(total_sql)

    # By type
    type_sql = f"""\
        SELECT w.type,
               COUNT(DISTINCT w.id) as workouts,
               COUNT(s.id) as sets,
               COALESCE(ROUND(SUM(s.weight_kg * s.reps)), 0) as volume
        FROM workouts w
        JOIN sets s ON w.id = s.workout_id
        WHERE w.owner = '{_owner(request)}'
        GROUP BY w.type
        ORDER BY w.type
    """
    by_type = _run_sql(type_sql)

    # By exercise
    ex_sql = f"""\
        SELECT e.name, e.name_cn, e.category,
               COUNT(DISTINCT w.id) as sessions,
               COUNT(s.id) as total_sets,
               ROUND(AVG(s.weight_kg), 1) as avg_weight,
               MAX(s.weight_kg) as max_weight,
               COALESCE(ROUND(SUM(s.weight_kg * s.reps)), 0) as total_volume
        FROM exercises e
        LEFT JOIN sets s ON e.id = s.exercise_id AND s.owner = '{_owner(request)}'
        LEFT JOIN workouts w ON s.workout_id = w.id AND w.owner = '{_owner(request)}'
        GROUP BY e.id, e.name, e.category
        HAVING total_sets > 0
        ORDER BY total_volume DESC
    """
    ex_data = _run_sql(ex_sql)
    if ex_data:
        ex_data = [_adjust(r) for r in ex_data]

    # Last 5 sessions
    recent_sql = f"""\
        SELECT w.id, w.date, w.type, w.duration_min, w.summary,
               COUNT(s.id) as sets,
               COALESCE(ROUND(SUM(s.weight_kg * s.reps)), 0) as volume
        FROM workouts w
        JOIN sets s ON w.id = s.workout_id
        WHERE w.owner = '{_owner(request)}'
        GROUP BY w.id, w.date, w.type, w.duration_min, w.summary
        ORDER BY w.date DESC
        LIMIT 5
    """
    recent = _run_sql(recent_sql)

    # Latest set per exercise
    owner = _owner(request)
    latest_sql = f"""\
        SELECT e.name, e.name_cn, e.category, s.weight_kg, s.reps, w.date
        FROM sets s
        JOIN workouts w ON s.workout_id = w.id
        JOIN exercises e ON s.exercise_id = e.id
        WHERE s.owner = '{owner}'
        AND s.id IN (
            SELECT MAX(s2.id) FROM sets s2
            JOIN workouts w2 ON s2.workout_id = w2.id
            WHERE s2.owner = '{owner}' AND s2.exercise_id = s.exercise_id
            GROUP BY s2.exercise_id
        )
        ORDER BY e.category, e.name
    """
    latest_sets = _run_sql(latest_sql)
    if latest_sets:
        latest_sets = [_adjust(r) for r in latest_sets]

    # ── Personal Records ──
    pr_sql = f"""\
        SELECT e.name, e.name_cn, e.category, s.weight_kg, s.reps, w.date
        FROM sets s
        JOIN workouts w ON s.workout_id = w.id
        JOIN exercises e ON s.exercise_id = e.id
        JOIN (
            SELECT s2.exercise_id, MAX(s2.weight_kg) as max_wt
            FROM sets s2 WHERE s2.owner = '{owner}'
            GROUP BY s2.exercise_id
        ) m ON s.exercise_id = m.exercise_id AND s.weight_kg = m.max_wt
        WHERE s.owner = '{owner}'
        AND s.id = (
            SELECT s3.id FROM sets s3
            WHERE s3.exercise_id = s.exercise_id
            AND s3.weight_kg = s.weight_kg
            AND s3.owner = '{owner}'
            ORDER BY s3.reps DESC, s3.id DESC
            LIMIT 1
        )
        ORDER BY s.weight_kg DESC
        LIMIT 20
    """
    prs = _run_sql(pr_sql)
    if prs:
        prs = [_adjust(r) for r in prs]

    return Response({
        'totals': totals[0] if totals else {},
        'by_type': by_type or [],
        'exercises': ex_data or [],
        'recent': recent or [],
        'latest_sets': latest_sets or [],
        'prs': prs or [],
    })


# ── cycle info ──────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def cycle_detail(request):
    """Get current cycle info (most recent), or create a new one."""
    if request.method == 'GET':
        data = _run_sql(f"SELECT * FROM cycle_info WHERE owner = '{_owner(request)}' ORDER BY id DESC LIMIT 1")
        if not data:
            return Response({'error': '尚无 cycle 数据'}, status=404)
        return Response(data[0])

    # POST — create new cycle
    pattern = request.data.get('pattern')
    rest_day = request.data.get('rest_day')
    start_date = request.data.get('start_date')
    note = request.data.get('note', '')

    if not pattern or not rest_day:
        return Response({'error': 'pattern 和 rest_day 必填'}, status=400)

    date_sql = f"'{start_date}'" if start_date else "NULL"
    note_sql = f"'{note.replace(chr(39), chr(39)+chr(39))}'" if note else "NULL"

    sql = f"""\
        INSERT INTO cycle_info (id, pattern, rest_day, start_date, note, owner)
        VALUES (nextval('seq_cycle_id'), '{pattern}', '{rest_day}',
                {date_sql}, {note_sql}, '{_owner(request)}')
        RETURNING id
    """
    raw = _run_workout_query(sql)
    if not raw:
        return Response({'error': '创建失败'}, status=500)

    rows = _parse_duckdb_table(raw)
    return Response({'id': rows[0]['id'], 'pattern': pattern, 'rest_day': rest_day}, status=201)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def cycle_update(request, pk):
    """Update a cycle entry."""
    updates = []
    for field in ('pattern', 'rest_day', 'start_date', 'note'):
        if field in request.data:
            val = request.data[field]
            if val is None:
                updates.append(f"{field} = NULL")
            elif field in ('pattern', 'rest_day', 'note'):
                safe = val.replace(chr(39), chr(39) + chr(39))
                updates.append(f"{field} = '{safe}'")
            else:
                updates.append(f"{field} = '{val}'")

    if not updates:
        return Response({'error': '没有可更新的字段'}, status=400)

    sql = f"UPDATE cycle_info SET {', '.join(updates)} WHERE id = {pk} AND owner = '{_owner(request)}'"
    _run_workout_query(sql)
    return Response({'status': 'updated', 'id': pk})


# ── users ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def api_users(request):
    """List all users who have workout data."""
    sql = "SELECT DISTINCT owner FROM workouts ORDER BY owner"
    data = _run_sql(sql)
    if data is None:
        return Response({'error': '查询失败'}, status=500)
    owners = [row['owner'] for row in data]

    # Also include users from wechat_binds that may not have workouts yet
    binds_sql = "SELECT DISTINCT username FROM wechat_binds ORDER BY username"
    binds = _run_sql(binds_sql)
    if binds:
        bound_users = [r['username'] for r in binds]
        for u in bound_users:
            if u not in owners:
                owners.append(u)
        owners.sort()

    return Response(owners)


# ── WeChat login ────────────────────────────────────────────────────

import json
import urllib.request
import urllib.parse

@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_login(request):
    """Exchange wx code for openid, check if bound to a user."""
    code = request.data.get('code')
    if not code:
        return Response({'error': 'code 必填'}, status=400)

    appid = settings.WX_APPID
    secret = settings.WX_APPSECRET

    url = (f"https://api.weixin.qq.com/sns/jscode2session?"
           f"appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code")

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
    except Exception as e:
        return Response({'error': '微信登录失败'}, status=502)

    openid = body.get('openid')
    if not openid:
        return Response({'error': '微信登录失败', 'detail': body.get('errmsg', '')}, status=400)

    # Check if bound
    safe_openid = openid.replace("'", "''")
    rows = _run_sql(f"SELECT username FROM wechat_binds WHERE openid = '{safe_openid}'")
    username = rows[0]['username'] if rows else None

    return Response({
        'openid': openid,
        'bound': username is not None,
        'username': username,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_bind(request):
    """Bind openid to an existing username."""
    openid = request.data.get('openid')
    username = request.data.get('username')

    if not openid or not username:
        return Response({'error': 'openid 和 username 必填'}, status=400)

    # Check if openid already bound
    safe_openid = openid.replace("'", "''")
    existing = _run_sql(f"SELECT username FROM wechat_binds WHERE openid = '{safe_openid}'")
    if existing:
        return Response({'error': '该微信已绑定用户: ' + existing[0]['username']}, status=400)

    # Check if username already bound by another wechat
    safe_user = username.replace("'", "''")
    user_bound = _run_sql(f"SELECT openid FROM wechat_binds WHERE username = '{safe_user}'")
    if user_bound:
        return Response({'error': '该用户已被其他微信绑定'}, status=400)

    # Check if username exists in workouts
    user_exists = _run_sql(f"SELECT 1 FROM workouts WHERE owner = '{safe_user}' LIMIT 1")
    if not user_exists:
        return Response({'error': '用户不存在或没有训练数据'}, status=400)

    # Create bind
    _run_workout_query(
        f"INSERT INTO wechat_binds (openid, username) VALUES ('{safe_openid}', '{safe_user}')"
    )
    return Response({'status': 'bound', 'username': username})


@api_view(['POST'])
@permission_classes([AllowAny])
def wechat_create(request):
    """Create a new user and bind wechat openid to it."""
    openid = request.data.get('openid')
    username = request.data.get('username')

    if not openid or not username:
        return Response({'error': 'openid 和 username 必填'}, status=400)

    safe_openid = openid.replace("'", "''")
    safe_user = username.replace("'", "''")

    # Check if openid already bound
    existing = _run_sql(f"SELECT username FROM wechat_binds WHERE openid = '{safe_openid}'")
    if existing:
        return Response({'error': '该微信已绑定用户: ' + existing[0]['username']}, status=400)

    # Check if username taken
    user_exists = _run_sql(f"SELECT 1 FROM workouts WHERE owner = '{safe_user}' LIMIT 1")
    if user_exists:
        return Response({'error': '用户名已存在'}, status=400)

    # Create bind + user will have data when they first work out
    _run_workout_query(
        f"INSERT INTO wechat_binds (openid, username) VALUES ('{safe_openid}', '{safe_user}')"
    )
    return Response({'status': 'created', 'username': username}, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def wechat_unbound(request):
    """List users not bound to any wechat account."""
    sql = """\
        SELECT DISTINCT w.owner
        FROM workouts w
        LEFT JOIN wechat_binds b ON w.owner = b.username
        WHERE b.openid IS NULL
        ORDER BY w.owner
    """
    data = _run_sql(sql)
    if data is None:
        return Response({'error': '查询失败'}, status=500)
    return Response([row['owner'] for row in data])


@api_view(['GET'])
@permission_classes([AllowAny])
def exercise_gif(request):
    """Return GIF URL for an exercise name."""
    name = request.query_params.get('name', '')
    if not name:
        return Response({'error': 'name 必填'}, status=400)
    safe = name.replace("'", "''")
    rows = _run_sql(f"SELECT exercise_name, gif_path FROM exercise_gifs WHERE exercise_name = '{safe}'")
    if not rows:
        return Response({'gif_url': None})
    path = rows[0]['gif_path']
    # Convert file path to URL
    filename = path.split('/')[-1]
    return Response({'gif_url': f'https://avocadocloud.duckdns.org/images/ex-demos/all/{filename}'})


@api_view(['POST'])
@permission_classes([AllowAny])
def timer_notify(request):
    """Send WeChat subscribe message when timer expires."""
    owner = request.data.get('owner', '').replace("'", "''")
    minutes = request.data.get('minutes', 0)

    if not owner:
        return Response({'error': 'owner 必填'}, status=400)

    # Look up openid
    rows = _run_sql(f"SELECT openid FROM wechat_binds WHERE username = '{owner}'")
    if not rows:
        return Response({'error': '未找到微信绑定'}, status=404)
    openid = rows[0]['openid']

    # Get access_token
    appid = settings.WX_APPID
    secret = settings.WX_APPSECRET
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
    try:
        req = urllib.request.Request(token_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_data = json.loads(resp.read())
        token = token_data.get('access_token')
        if not token:
            return Response({'error': '获取token失败', 'detail': token_data}, status=502)
    except Exception as e:
        return Response({'error': 'token请求失败'}, status=502)

    # Send subscribe message
    from datetime import datetime, timedelta
    end_time = (datetime.now() + timedelta(minutes=minutes)).strftime('%H:%M')
    tmpl_id = 'lsf68_WyUqKrYTi1UhwPpcmbpBjsUZ69EX7-Maw-Tw0'
    send_url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}"
    body = {
        'touser': openid,
        'template_id': tmpl_id,
        'data': {
            'thing7': {'value': '组间休息'},
            'time2': {'value': end_time},
        },
        'page': 'pages/home/home',
    }
    try:
        req2 = urllib.request.Request(send_url, data=json.dumps(body).encode(), method='POST')
        req2.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            result = json.loads(resp2.read())
        if result.get('errcode', -1) == 0:
            return Response({'status': 'sent'})
        else:
            return Response({'status': 'failed', 'detail': result}, status=502)
    except Exception as e:
        return Response({'error': '发送通知失败'}, status=502)

# API Docs
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_docs(request):
    base = "https://avocadocloud.duckdns.org/api/fitness"
    apis = [
        ("GET", "/workouts/", "?owner=howard&limit=20", "训练记录列表"),
        ("POST", "/workouts/", '{"owner":"howard","type":"Push"}', "创建训练"),
        ("GET", "/workouts/last/", "?owner=howard&offset=0", "上次训练(N次前)"),
        ("PATCH", "/workouts/59/", '{"duration_min":60}', "更新时长/备注"),
        ("GET", "/exercises/", "?owner=howard", "动作列表"),
        ("POST", "/sets/", '{"workout_id":59,"exercise_id":1,"weight_kg":55,"reps":12,"set_number":1}', "记录一组"),
        ("GET", "/sets/history/", "?owner=howard&exercise_id=1&limit=50", "某动作历史"),
        ("GET", "/stats/", "?owner=howard", "统计数据(PR/分布/周量)"),
        ("GET", "/cycle/", "?owner=howard", "当前训练循环"),
        ("POST", "/cycle/", '{"push_a_cal":2000,"pull_a_cal":1800}', "创建循环"),
        ("PATCH", "/cycle/1/", '{"push_a_cal":2100}', "更新循环"),
        ("GET", "/users/", "", "用户列表"),
        ("POST", "/wechat/login/", '{"code":"wx_login_code"}', "微信登录"),
        ("POST", "/wechat/bind/", '{"openid":"xxx","username":"howard"}', "绑定用户"),
        ("POST", "/wechat/create/", '{"openid":"xxx","username":"new"}', "创建并绑定"),
        ("GET", "/wechat/unbound/", "", "未绑定用户"),
        ("GET", "/exercise-gif/", "?name=barbell+bench+press&owner=howard", "动作GIF"),
        ("POST", "/timer-notify/", '{"minutes":3}', "倒计时通知"),
    ]
    rows = []
    for method, path, params, desc in apis:
        ex = path + (params if params.startswith('?') else '')
        curl = f"curl -X {method} '{base}{ex}' -H 'Referer: {base}'" 
        if params and not params.startswith('?'):
            curl += f" -d '{params}' -H 'Content-Type: application/json'"
        rows.append(f"<tr><td class=m>{method}</td><td><code>{path}</code><br><small>{desc}</small></td><td><code class=c>{curl}</code></td></tr>")

    html = f"""<!DOCTYPE html>
<html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Fitness API</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#e6edf3;font:14px monospace;padding:24px;max-width:960px;margin:0 auto}}
h1{{color:#58a6ff;font-size:18px;margin-bottom:4px}}
.sub{{color:#8b949e;font-size:12px;margin-bottom:16px}}
table{{border-collapse:collapse;width:100%;font-size:12px}}
th,td{{border:1px solid #30363d;padding:6px 8px;vertical-align:top}}
th{{background:#161b22;position:sticky;top:0}}
tr:hover{{background:#1c2128}}
code{{background:#161b22;padding:1px 4px;border-radius:3px;font-size:11px}}
.c{{color:#7ee787;word-break:break-all;font-size:11px}}
.m{{color:#f0883e;font-weight:bold;white-space:nowrap}}
small{{color:#8b949e}}
</style></head><body>
<h1>Fitness API</h1>
<p class=sub><code>{base}/</code> | Auth: GET login -> csrftoken -> POST login -> X-CSRFToken + Referer | 所有请求需 owner 参数(QQ bot 必传body)</p>
<table><tr><th>Method</th><th>Endpoint</th><th>Example</th></tr>
{''.join(rows)}
</table></body></html>"""
    return HttpResponse(html)


# ── tiers（段位）─────────────────────────────────────────────────────

def _num(v):
    """DuckDB CLI 输出的 'NULL' 是字符串，必须手动转 None。"""
    if v is None:
        return None
    s = str(v).strip()
    if s == '' or s.upper() == 'NULL':
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _str(v):
    """字符串列同理：DuckDB CLI 的 NULL 也输出成 'NULL' 字面量，必须转成 JSON null。

    （2026-09-24 踩过：引体向上的 cur_target 返回了字符串 "NULL"，前端拿到会当有效值）
    """
    if v is None:
        return None
    s = str(v).strip()
    return None if (s == '' or s.upper() == 'NULL') else s


@api_view(['GET'])
@permission_classes([AllowAny])
def tiers_status(request):
    """当前各项能力段位 + 到下一段的进度（数据源：DuckDB 的 tiers 表）。

    tiers 表由 VPS 上的 tier_check.py 在每次收工检测段位时自动刷新。
    返回每条含：lift/metric/cur_value/e1rm_kg/tier/tier_index/tier_floor/
    next_tier/next_need/gap/progress/progress_pct/next_e1rm_kg/bodyweight/best_date
    """
    sql = f"""
        SELECT lift, metric, cur_value, e1rm_kg, tier, tier_index, tier_floor,
               next_tier, next_need, gap, bodyweight, next_working_kg, next_working_reps,
               next_target, cur_working_kg, cur_working_reps, cur_target,
               prev_progress, cur_progress, progress_delta,
               best_date, updated_at
        FROM tiers
        WHERE owner = '{_owner(request)}'
        ORDER BY tier_index DESC, gap ASC NULLS LAST
    """
    rows = _run_sql(sql) or []
    out = []
    for r in rows:
        cur = _num(r.get('cur_value')) or 0.0
        floor = _num(r.get('tier_floor')) or 0.0
        need = _num(r.get('next_need'))
        pct = None
        if need is not None:
            pct = 0.0 if need <= floor else max(0.0, min(1.0, (cur - floor) / (need - floor)))
        bw = _num(r.get('bodyweight'))
        metric = r.get('metric')
        out.append({
            'lift': _str(r.get('lift')),
            'metric': _str(r.get('metric')),
            'cur_value': round(cur, 3),
            'e1rm_kg': (round(_num(r.get('e1rm_kg')), 1) if _num(r.get('e1rm_kg')) else None),
            'tier': _str(r.get('tier')),
            'tier_index': int(_num(r.get('tier_index')) or 0),
            'tier_floor': round(floor, 3),
            'next_tier': _str(r.get('next_tier')),
            'next_need': (round(need, 3) if need is not None else None),
            'gap': (round(_num(r.get('gap')), 3) if _num(r.get('gap')) is not None else None),
            'progress': (round(pct, 4) if pct is not None else None),
            'progress_pct': (round(pct * 100) if pct is not None else None),
            'next_e1rm_kg': (round(need * bw, 1) if (metric == 'ratio' and need and bw) else None),
            # 可执行目标：重量 × 次数（他没推过极限，做组重量才是能直接执行的）
            'next_working_kg': _num(r.get('next_working_kg')),
            'next_working_reps': (int(_num(r.get('next_working_reps')))
                                  if _num(r.get('next_working_reps')) else None),
            'next_target': _str(r.get('next_target')),
            # 当前做组数据 = 产出当前 e1RM 的那一组（与 e1rm_kg/段位/进度严格同源）
            'cur_working_kg': _num(r.get('cur_working_kg')),
            'cur_working_reps': (int(_num(r.get('cur_working_reps')))
                                 if _num(r.get('cur_working_reps')) else None),
            'cur_target': _str(r.get('cur_target')),
            # 本次进度变化（相对上一次训练）；升段时 progress_delta 为 null（进度已重置）
            'prev_progress_pct': _num(r.get('prev_progress')),
            'cur_progress_pct': _num(r.get('cur_progress')),
            'progress_delta': _num(r.get('progress_delta')),
            'bodyweight': bw,
            'best_date': _str(r.get('best_date')),
        })
    return Response({
        'count': len(out),
        'updated_at': (rows[0].get('updated_at') if rows else None),
        'bodyweight': (out[0]['bodyweight'] if out else None),
        'results': out,
    })


# ── tiers legend（段位表 + 配色，供前端渲染弹窗）────────────────────

# 展示用的配色 / emoji（集中在这里，前端不再硬编码）
# 弹窗（段位对照表）里的 3 个主项
LEGEND_PRIMARY = ('杠铃深蹲', '杠铃卧推', '引体向上')
LEGEND_REPS = 10                 # 做组重量的口径：10 次
DEFAULT_BODYWEIGHT = 75.0        # bodyweight 表里没记录时的兜底体重

# 每档人物画像（profile = 画像 / marker = 标志）—— 故意不含具体公斤数，避免与阈值脱节
TIER_PROFILE = [
    ('刚进健身房，动作还在学。', '先把动作和习惯建立起来，别急着加重量'),
    ('练了几个月，动作基本成型。', '已经是健身房里"会练"的那一半'),
    ('入门完成，重量开始像样。', '卧推 1× 体重、深蹲 1.5× 体重 —— 力量训练的及格线'),
    ('健身房里的中上水平。', '深蹲 300 磅 / 卧推 200 磅 —— 公认的"强壮线"'),
    ('业余练家里很少见。', '同体重的人里，你已经在前面那一小撮'),
    ('接近力量举业余门槛。', '开始有人主动问你"怎么练的"'),
    ('业余顶尖。', '大概率是你所在健身房同体重最强的那几个'),
    ('万里挑一，竞赛级水准。', '同体重下的顶级表现'),
]

TIER_STYLE = [
    ('倔强青铜', '#8b6b4a', '🥉'),
    ('秩序白银', '#a8b3b8', '🥈'),
    ('荣耀黄金', '#f5c342', '🥇'),
    ('尊贵铂金', '#7fd8e8', '💠'),
    ('永恒钻石', '#a78bfa', '💎'),
    ('至尊星耀', '#f778ba', '⭐'),
    ('最强王者', '#ff7b72', '👑'),
    ('荣耀王者', '#ffb020', '🏆'),
]


@api_view(['GET'])
@permission_classes([AllowAny])
def tiers_legend(request):
    """段位对照表（弹窗用）：阈值 + 配色 + 做组重量 + 人物画像。

    数据源：DuckDB `tier_ladder` 表（tier_check.py 每次运行同步）+ `bodyweight` 表（当前体重）。
    → 体重一变，返回的公斤数自动跟着变；阈值只在后端维护，前端不用硬编码 ✓

    GET /api/fitness/tiers/legend/?owner=xxx   （owner 只用于取体重，默认 howard）
    """
    owner = _owner(request)
    rows = _run_sql("""
        SELECT lift, exercise_id, metric, tier_index, threshold, sort_order, increment
        FROM tier_ladder ORDER BY sort_order, tier_index
    """) or []

    bw_rows = _run_sql(
        f"SELECT kg FROM bodyweight WHERE owner = '{owner}' ORDER BY date DESC LIMIT 1"
    ) or []
    bw = _num(bw_rows[0].get('kg')) if bw_rows else None
    bw_source = 'table' if bw else 'default'
    bw = bw or DEFAULT_BODYWEIGHT

    lifts, index = [], {}
    for r in rows:
        name = _str(r.get('lift'))
        if name not in index:
            metric = _str(r.get('metric'))
            inc = _num(r.get('increment')) or 0
            index[name] = {
                'lift': name,
                'exercise_id': int(_num(r.get('exercise_id')) or 0),
                'metric': metric,
                'unit': ('倍' if metric == 'ratio' else '个'),
                'increment': inc or None,
                'on_legend': name in LEGEND_PRIMARY,
                'thresholds': [],
                'working_kg_10': [],
            }
            lifts.append(index[name])
        spec = index[name]
        th = _num(r.get('threshold'))
        spec['thresholds'].append(th)
        if spec['metric'] == 'ratio' and spec['increment'] and th:
            # 目标 e1RM = 阈值 × 体重 → 反算 10 次的做组重量 → 向上取整到加重档位
            raw = (th * bw) / (1 + LEGEND_REPS / 30.0)
            inc = spec['increment']
            spec['working_kg_10'].append(round(math.ceil(round(raw / inc, 6)) * inc, 2))
        else:
            spec['working_kg_10'].append(None)   # 地板档(0) 与 reps 型 → null

    return Response({
        'count': len(lifts),
        'bodyweight': bw,
        'bodyweight_source': bw_source,          # 'table'（体重视图）| 'default'（兜底值）
        'bodyweight_owner': owner,
        'reps_for_working': LEGEND_REPS,
        'tiers': [{'name': n, 'index': i, 'color': c, 'emoji': e,
                   'profile': (TIER_PROFILE[i][0] if i < len(TIER_PROFILE) else ''),
                   'marker': (TIER_PROFILE[i][1] if i < len(TIER_PROFILE) else '')}
                  for i, (n, c, e) in enumerate(TIER_STYLE)],
        'lifts': lifts,
        'legend_order': [x['lift'] for x in lifts if x['on_legend']],
        'notes': [
            '核心动作按「e1RM（估算最大力量）÷ 体重」的倍数分档',
            '引体向上按单组最多次数分档',
            '孤立动作与器械动作不评段位（体重倍数对它们没有意义）',
            f'working_kg_10 = 达到该档位所需的「做组重量 × {LEGEND_REPS}」（已按当前体重换算，向上取整到加重档位）',
            '第 0 档（地板档）的 working_kg_10 为 null，前端显示成「< 下一档的值」',
            '体重变化自动重算（数据源 bodyweight 表）',
            '阈值与文案只在后端维护，前端不用硬编码',
        ],
    })


# ── bodyweight（体重记录）────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def bodyweight_log(request):
    """体重记录。

    GET  /api/fitness/bodyweight/?owner=xxx         → 全部记录（按日期升序）+ 最新一条
    POST /api/fitness/bodyweight/                    → 记一条 {owner, date, kg}

    用途：段位按「e1RM ÷ 体重」算，体重会变 —— 有了这张表就按训练当天的体重算，
    不用改脚本常量（2026-09-24 加的）。
    """
    owner = _owner(request)

    if request.method == 'GET':
        sql = f"""
            SELECT date, kg FROM bodyweight
            WHERE owner = '{owner}' ORDER BY date
        """
        rows = _run_sql(sql) or []
        out = [{'date': _str(r.get('date')), 'kg': _num(r.get('kg'))} for r in rows]
        return Response({
            'count': len(out),
            'latest': (out[-1] if out else None),
            'results': out,
        })

    # POST：记一条
    day = str(request.data.get('date') or datetime.date.today().isoformat())
    kg = request.data.get('kg', request.data.get('weight_kg'))
    try:
        kg = float(kg)
        datetime.date.fromisoformat(day)
    except (TypeError, ValueError):
        return Response({'error': 'date(YYYY-MM-DD) 与 kg 必填且格式正确'}, status=400)
    if not 20 <= kg <= 300:
        return Response({'error': 'kg 需在 20–300 之间'}, status=400)

    _run_workout_query(
        f"DELETE FROM bodyweight WHERE owner = '{owner}' AND date = DATE '{day}';"
    )
    _run_workout_query(
        f"INSERT INTO bodyweight VALUES ('{owner}', DATE '{day}', {kg}, now())"
    )
    return Response({'status': 'created', 'owner': owner, 'date': day, 'kg': kg}, status=201)
