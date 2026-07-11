const BASE_URL = 'https://cucumberonmoon.duckdns.org'

// 当前选中的用户
let _currentUser = ''

function setCurrentUser(username) {
  _currentUser = username
  wx.setStorageSync('selectedUser', username)
}

function getCurrentUser() {
  if (!_currentUser) {
    _currentUser = wx.getStorageSync('selectedUser') || ''
  }
  return _currentUser
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    let url = BASE_URL + path
    const header = { 'Content-Type': 'application/json' }

    // GET 请求：owner 拼到 URL
    if (method === 'GET') {
      const owner = getCurrentUser()
      const sep = url.includes('?') ? '&' : '?'
      url += sep + 'owner=' + encodeURIComponent(owner || 'howard')
    }

    wx.request({
      url: url,
      method: method,
      header: header,
      data: method === 'GET' ? undefined : data,
      success: res => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(new Error(res.data?.error || '请求失败'))
        }
      },
      fail: err => reject(new Error('网络错误：' + err.errMsg))
    })
  })
}

// 获取用户列表
function getUsers() {
  return request('GET', '/api/fitness/users/')
}

// 统计概览
function getStats() {
  return request('GET', '/api/fitness/stats/')
}

// 获取动作列表
function getExercises() {
  return request('GET', '/api/fitness/exercises/')
}

// 获取 cycle
function getCycle() {
  return request('GET', '/api/fitness/cycle/')
}

// 创建训练
function startWorkout(data) {
  return request('POST', '/api/fitness/workouts/', data || { owner: getCurrentUser() })
}

// 记录一组
function logSet(workoutId, exerciseId, weight, reps, rir) {
  return request('POST', '/api/fitness/sets/', {
    workout: workoutId,
    exercise: exerciseId,
    weight_kg: weight,
    reps: reps,
    rir: rir || 0,
    owner: getCurrentUser()
  })
}

// 完成训练
function finishWorkout(workoutId, durationMin) {
  return request('PATCH', '/api/fitness/workouts/' + workoutId + '/', {
    duration_min: durationMin,
    owner: getCurrentUser()
  })
}

// 获取历史
function getWorkouts(limit) {
  if (limit === undefined) limit = 20
  return request('GET', '/api/fitness/workouts/', { limit: limit })
}

module.exports = {
  setCurrentUser, getCurrentUser,
  getUsers, getStats, getExercises, getCycle,
  startWorkout, logSet, finishWorkout,
  getWorkouts
}
