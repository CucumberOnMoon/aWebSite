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

// 用户列表
function getUsers() { return request('GET', '/api/fitness/users/') }
function getUnbound() { return request('GET', '/api/fitness/wechat/unbound/') }

// 微信登录
function wechatLogin(code) { return request('POST', '/api/fitness/wechat/login/', { code }) }
function wechatBind(openid, username) { return request('POST', '/api/fitness/wechat/bind/', { openid, username }) }
function wechatCreate(openid, username) { return request('POST', '/api/fitness/wechat/create/', { openid, username }) }

// 统计 & 训练
function getStats() { return request('GET', '/api/fitness/stats/') }
function getExercises() { return request('GET', '/api/fitness/exercises/') }
function getCycle() { return request('GET', '/api/fitness/cycle/') }
function startWorkout(data) { return request('POST', '/api/fitness/workouts/', data || { owner: getCurrentUser() }) }
function logSet(workoutId, exerciseId, weight, reps, rir) {
  return request('POST', '/api/fitness/sets/', { workout: workoutId, exercise: exerciseId, weight_kg: weight, reps, rir: rir || 0, owner: getCurrentUser() })
}
function finishWorkout(workoutId, durationMin) {
  return request('PATCH', '/api/fitness/workouts/' + workoutId + '/', { duration_min: durationMin, owner: getCurrentUser() })
}
function getWorkouts(limit) { return request('GET', '/api/fitness/workouts/', { limit: limit || 20 }) }
function getLastWorkout() { return request('GET', '/api/fitness/workouts/last/') }
function getSetHistory(exerciseId) {
  return request('GET', '/api/fitness/sets/history/', { exercise_id: exerciseId })
}

module.exports = {
  setCurrentUser, getCurrentUser,
  getUsers, getUnbound, wechatLogin, wechatBind, wechatCreate,
  getStats, getExercises, getCycle,
  startWorkout, logSet, finishWorkout, getWorkouts, getLastWorkout,
  getSetHistory
}
