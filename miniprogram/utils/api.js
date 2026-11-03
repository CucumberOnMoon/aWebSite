const BASE_URL = 'https://avocadocloud.duckdns.org'

// 主用户（默认 owner）
// 改名只改这里一处
const MAIN_OWNER = '夯嘚嫑嫑啲'

let _currentUser = ''

function setCurrentUser(username) {
  // ⚠️ 不能 toLowerCase：owner 在 DuckDB 里区分大小写，
  // 库里同时存在 Lucy 和 lucy（两个不同的人），转小写会永久屏蔽大写用户的数据。
  _currentUser = username || ''
  wx.setStorageSync('selectedUser', _currentUser)
}

function getCurrentUser() {
  if (!_currentUser) _currentUser = wx.getStorageSync('selectedUser') || ''
  return _currentUser
}

// 微信身份：openid 由 wx.login → /wechat/login 换取，写操作靠它定 owner
function setOpenid(v) {
  wx.setStorageSync('openid', v || '')
}

function getOpenid() {
  return wx.getStorageSync('openid') || ''
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    let url = BASE_URL + path
    const header = { 'Content-Type': 'application/json' }
    const openid = getOpenid()
    if (openid) header['X-Openid'] = openid
    if (method === 'GET') {
      const params = []
      params.push('owner=' + encodeURIComponent(getCurrentUser() || MAIN_OWNER))
      params.push('_t=' + Date.now())  // 防缓存
      if (data && typeof data === 'object') {
        for (const [k, v] of Object.entries(data)) {
          if (v !== undefined && v !== null) params.push(k + '=' + encodeURIComponent(v))
        }
      }
      url += (url.includes('?') ? '&' : '?') + params.join('&')
    }
    wx.request({
      url, method, header,
      data: method === 'GET' ? undefined : data,
      success: res => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data)
        else reject(new Error(res.data?.error || '请求失败'))
      },
      fail: err => reject(new Error('网络错误：' + err.errMsg))
    })
  })
}

// 用户列表（前端兜底过滤，规则与后端 OwnerValidationMiddleware 保持一致）
const OWNER_RE = /^[A-Za-z0-9_\u4e00-\u9fa5-]{1,20}$/
function isValidOwner(name) {
  return typeof name === 'string' && OWNER_RE.test(name)
}
function getUsers() {
  return request('GET', '/api/fitness/users/').then(list => {
    if (!Array.isArray(list)) return []
    // 只过滤脏数据，**按原样去重**：Lucy 和 lucy 是数据库里两个不同的人，
    // 按小写去重会把其中一个人的数据入口吞掉。
    const seen = {}
    const out = []
    for (const name of list) {
      if (!isValidOwner(name)) continue
      if (seen[name]) continue
      seen[name] = true
      out.push(name)
    }
    out.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
    return out
  })
}
function getUnbound(openid) { return request('GET', '/api/fitness/wechat/unbound/', openid ? { openid } : undefined) }

// 微信登录
function wechatLogin(code) { return request('POST', '/api/fitness/wechat/login/', { code }) }
function wechatBind(openid, username) { return request('POST', '/api/fitness/wechat/bind/', { openid, username }) }
function wechatCreate(openid, username) { return request('POST', '/api/fitness/wechat/create/', { openid, username }) }

// 训练计划（按 owner 存；写操作身份由后端按 X-Openid 强制决定）
function getPlan(dow) {
  return request('GET', '/api/fitness/plan/', dow === undefined ? null : { dow })
}
function savePlan(dow, type, items) {
  return request('POST', '/api/fitness/plan/', { dow, type, items: items || [] })
}
function deletePlan(dow) {
  return request('DELETE', '/api/fitness/plan/?dow=' + encodeURIComponent(dow) + '&_t=' + Date.now())
}

// 统计 & 训练
function getStats() { return request('GET', '/api/fitness/stats/') }
function getTiers() { return request('GET', '/api/fitness/tiers/') }
function getTiersLegend() { return request('GET', '/api/fitness/tiers/legend/') }
function getExercises() { return request('GET', '/api/fitness/exercises/') }
// 首页聚合：一次拿齐 stats / workouts / compound / last / tiers
// （原先要发 12 个请求，4 段串行 + 7 个主项历史逐个拉，首屏 5-7 秒）
function getHome(data) { return request('GET', '/api/fitness/home/', data || {}) }
function startWorkout(data) { return request('POST', '/api/fitness/workouts/', data || { owner: getCurrentUser() }) }
function logSet(workoutId, exerciseId, weight, reps, rir, setNumber) {
  return request('POST', '/api/fitness/sets/', {
    workout_id: workoutId, exercise_id: exerciseId,
    weight_kg: weight, reps, rpe: rir || 0,
    set_number: setNumber,
    owner: getCurrentUser()
  })
}
function finishWorkout(workoutId, durationMin) {
  return request('PATCH', '/api/fitness/workouts/' + workoutId + '/', { duration_min: durationMin, owner: getCurrentUser() })
}
function getWorkouts(limit) { return request('GET', '/api/fitness/workouts/', { limit: limit || 20 }) }
function getLastWorkout(offset) { return request('GET', '/api/fitness/workouts/last/', { offset: offset || 0 }) }
function getSetHistory(exerciseId) {
  return request('GET', '/api/fitness/sets/history/', { exercise_id: exerciseId })
}
function getWorkoutSets(workoutId) {
  return request('GET', '/api/fitness/workouts/' + workoutId + '/')
}
function getExerciseGif(exerciseName) {
  return request('GET', '/api/fitness/exercise-gif/', { name: exerciseName })
}
// 动作详情：目标肌群 + 协同肌 + 注意事项 + 动图（一次拿全）
function getExerciseDetail(exerciseName) {
  return request('GET', '/api/fitness/exercise-detail/', { name: exerciseName })
}
function timerNotify(minutes, owner) {
  return request('POST', '/api/fitness/timer-notify/', { minutes, owner })
}

module.exports = {
  MAIN_OWNER,
  setCurrentUser, getCurrentUser, setOpenid, getOpenid,
  getUsers, getUnbound, wechatLogin, wechatBind, wechatCreate,
  getPlan, savePlan, deletePlan,
  getStats, getTiers, getTiersLegend, getExercises, getHome,
  startWorkout, logSet, finishWorkout, getWorkouts, getLastWorkout,
  getSetHistory, getWorkoutSets, getExerciseGif, getExerciseDetail, timerNotify
}
