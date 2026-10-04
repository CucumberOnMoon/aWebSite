const BASE_URL = 'https://avocadocloud.duckdns.org'

let _currentUser = ''

function setCurrentUser(username) {
  _currentUser = (username || '').toLowerCase()
  wx.setStorageSync('selectedUser', _currentUser)
}

function getCurrentUser() {
  if (!_currentUser) _currentUser = (wx.getStorageSync('selectedUser') || '').toLowerCase()
  return _currentUser
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    let url = BASE_URL + path
    const header = { 'Content-Type': 'application/json' }
    if (method === 'GET') {
      const params = []
      params.push('owner=' + encodeURIComponent(getCurrentUser() || 'howard'))
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
    // 过滤脏数据 + 按小写去重（后端 owner 匹配不区分大小写，避免 Lucy/lucy 重复出现）
    const seen = {}
    const out = []
    for (const name of list) {
      if (!isValidOwner(name)) continue
      const key = name.toLowerCase()
      if (seen[key]) continue
      seen[key] = true
      out.push(name)
    }
    out.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()))
    return out
  })
}
function getUnbound() { return request('GET', '/api/fitness/wechat/unbound/') }

// 微信登录
function wechatLogin(code) { return request('POST', '/api/fitness/wechat/login/', { code }) }
function wechatBind(openid, username) { return request('POST', '/api/fitness/wechat/bind/', { openid, username }) }
function wechatCreate(openid, username) { return request('POST', '/api/fitness/wechat/create/', { openid, username }) }

// 统计 & 训练
function getStats() { return request('GET', '/api/fitness/stats/') }
function getTiers() { return request('GET', '/api/fitness/tiers/') }
function getTiersLegend() { return request('GET', '/api/fitness/tiers/legend/') }
function getExercises() { return request('GET', '/api/fitness/exercises/') }
function getCycle() { return request('GET', '/api/fitness/cycle/') }
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
function timerNotify(minutes, owner) {
  return request('POST', '/api/fitness/timer-notify/', { minutes, owner })
}

module.exports = {
  setCurrentUser, getCurrentUser,
  getUsers, getUnbound, wechatLogin, wechatBind, wechatCreate,
  getStats, getTiers, getTiersLegend, getExercises, getCycle,
  startWorkout, logSet, finishWorkout, getWorkouts, getLastWorkout,
  getSetHistory, getWorkoutSets, getExerciseGif, timerNotify
}
