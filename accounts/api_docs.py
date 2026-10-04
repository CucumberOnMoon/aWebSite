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
