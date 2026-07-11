const BASE_URL = 'https://cucumberonmoon.duckdns.org'

// 小程序环境没有 btoa，手动实现
function base64Encode(str) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
  let out = '', i = 0
  while (i < str.length) {
    const b1 = str.charCodeAt(i++) || 0
    const b2 = str.charCodeAt(i++) || 0
    const b3 = str.charCodeAt(i++) || 0
    out += chars[(b1 >> 2) & 63]
    out += chars[((b1 << 4) | (b2 >> 4)) & 63]
    out += chars[((b2 << 2) | (b3 >> 6)) & 63]
    out += chars[b3 & 63]
  }
  // 补位 =
  const pad = str.length % 3
  if (pad === 1) out = out.slice(0, -2) + '=='
  else if (pad === 2) out = out.slice(0, -1) + '='
  return out
}

let _username = ''
let _password = ''

function setAuth(username, password) {
  _username = username
  _password = password
}

function clearAuth() {
  _username = ''
  _password = ''
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    const auth = _username + ':' + _password
    wx.request({
      url: BASE_URL + path,
      method: method,
      header: {
        'Authorization': 'Basic ' + base64Encode(auth),
        'Content-Type': 'application/json',
      },
      data: data,
      success: res => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else if (res.statusCode === 401 || res.statusCode === 403) {
          reject(new Error('UNAUTHORIZED'))
        } else {
          reject(new Error(res.data?.detail || '请求失败'))
        }
      },
      fail: err => reject(new Error('网络错误：' + err.errMsg))
    })
  })
}

// 验证登录（随便调个API试）
function checkAuth() {
  return request('GET', '/api/fitness/exercises/')
}

// 获取所有动作
function getExercises() {
  return request('GET', '/api/fitness/exercises/')
}

// 获取 cycle 信息（pattern, rest_day, start_date）
function getCycle() {
  return request('GET', '/api/fitness/cycle/')
}

// 创建训练
function startWorkout() {
  return request('POST', '/api/fitness/workouts/', {})
}

// 记录一组
function logSet(workoutId, exerciseId, weight, reps, rir) {
  return request('POST', '/api/fitness/sets/', {
    workout: workoutId,
    exercise: exerciseId,  // DuckDB: exercise_id
    weight_kg: weight,     // DuckDB: weight_kg
    reps: reps,
    rir: rir || 0
  })
}

// 完成训练（记时长）
function finishWorkout(workoutId, durationMin) {
  return request('PATCH', '/api/fitness/workouts/' + workoutId + '/', {
    duration_min: durationMin
  })
}

// 获取统计概览
function getStats() {
  return request('GET', '/api/fitness/stats/')
}

// 获取历史
function getWorkouts(limit) {
  if (limit === undefined) limit = 20
  return request('GET', '/api/fitness/workouts/', { limit: limit })
}

module.exports = {
  setAuth, clearAuth,
  checkAuth,
  getExercises, getCycle, getStats,
  startWorkout, logSet, finishWorkout,
  getWorkouts
}
