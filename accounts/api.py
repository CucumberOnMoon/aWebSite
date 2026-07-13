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

import logging
logger = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────────────

def _owner(request):
    """Get owner: from body for POST/PATCH, else from query param or fallback."""
    if request.method in ('POST', 'PATCH') and request.data.get('owner'):
        return request.data['owner']
    # GET: accept ?owner=xxx param, fallback to 'howard'
    return request.query_params.get('owner') or 'howard'

BODY_WEIGHT = 75
ASSISTED = {"助力引体向上", "双杠臂屈伸(助力)"}


def _adjust(row):
    """Same assisted-weight adjustment as the template view."""
    if row.get('name') in ASSISTED:
        if 'max_weight' in row and row['max_weight']:
            row['max_weight'] = round(BODY_WEIGHT - row['max_weight'], 1)
        if 'avg_weight' in row and row['avg_weight']:
            row['avg_weight'] = round(BODY_WEIGHT - row['avg_weight'], 1)
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
                   e.id as exercise_id, e.name as exercise, e.category
            FROM sets s
            JOIN exercises e ON s.exercise_id = e.id
            WHERE s.workout_id = {pk} AND s.owner = '{_owner(request)}'
            ORDER BY e.id, s.set_number
        """
        raw = _run_workout_query(sets_sql)
        data['sets'] = [_adjust(r) for r in (_parse_duckdb_table(raw) or [])] if raw else []
        return Response(data)

    # PATCH — update duration / note
    updates = []
    if 'duration_min' in request.data:
        val = request.data['duration_min']
        updates.append(f"duration_min = {val}" if val else "duration_min = NULL")
    if 'note' in request.data:
        n = request.data['note'].replace(chr(39), chr(39) + chr(39))
        updates.append(f"note = '{n}'" if n else "note = NULL")

    if not updates:
        return Response({'error': '没有可更新的字段'}, status=400)

    sql = f"UPDATE workouts SET {', '.join(updates)} WHERE id = {pk} AND owner = '{_owner(request)}'"
    _run_workout_query(sql)
    return Response({'status': 'updated', 'id': pk})


@api_view(['GET'])
@permission_classes([AllowAny])
def workout_last(request):
    """Most recent workout with full set details."""
    sql = f"SELECT id, date, type, duration_min, note FROM workouts WHERE owner = '{_owner(request)}' ORDER BY date DESC LIMIT 1"
    rows = _run_sql(sql)
    if not rows:
        return Response({'error': '尚无训练记录'}, status=404)

    data = rows[0]
    pk = data['id']
    sets_sql = f"""\
        SELECT s.id, s.set_number, s.weight_kg, s.reps, s.rpe,
               e.id as exercise_id, e.name as exercise, e.category
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
        SELECT e.name, e.category,
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
        SELECT w.id, w.date, w.type, w.duration_min,
               COUNT(s.id) as sets,
               COALESCE(ROUND(SUM(s.weight_kg * s.reps)), 0) as volume
        FROM workouts w
        JOIN sets s ON w.id = s.workout_id
        WHERE w.owner = '{_owner(request)}'
        GROUP BY w.id, w.date, w.type, w.duration_min
        ORDER BY w.date DESC
        LIMIT 5
    """
    recent = _run_sql(recent_sql)

    # Latest set per exercise
    owner = _owner(request)
    latest_sql = f"""\
        SELECT e.name, e.category, s.weight_kg, s.reps, w.date
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
        SELECT e.name, e.category, s.weight_kg, s.reps, w.date
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
