const api = require('../../utils/api')

const CAT_COLORS = { Push: '#f85149', Pull: '#d29922', Legs: '#3fb950' }
const EX_COLORS = ['#58a6ff', '#bc8cff', '#39d2c0', '#f5c342', '#f85149', '#3fb950', '#d29922', '#1f6feb', '#da3633', '#238636']

// Core compound lifts for strength curve
const COMPOUND_NAMES = ['杠铃深蹲', '杠铃卧推', '罗马尼亚硬拉', '硬拉']

Page({
  data: {
    loading: false,
    wxDone: false,
    userList: [],
    selectedUser: '',
    hasData: false,
    // 绑定相关
    showBind: false, showBindPicker: false, showCreate: false,
    wechatOpenid: '', unboundList: [], newUserName: '',

    // ── 6 大卡片数据 ──
    // ① 概览
    totals: {},
    // ② PR 记录
    prList: [],
    // ③ 力量曲线
    strengthLifts: [],
    // ④ 周训练量
    weeklyVolumes: [],
    // ⑤ 训练频率（日历）
    calGrid: [],
    calMonths: [],
    // ⑥ 推拉腿分布
    catBars: [],
    // ⑦ 上次训练详情
    lastWorkout: null,
    lastWorkoutStr: '',
    // ⑧ 亮点
    highlights: [],
  },

  async onShow() {
   if (!this.data.wxDone) {
     this.autoWechatLogin()
   } else {
     this.loadUsers()
     const saved = api.getCurrentUser()
     if (saved) {
       this.setData({ selectedUser: saved })
       this.loadAll(saved)
     }
   }
 },

 async autoWechatLogin() {
   this.setData({ wxDone: true })
   try {
     const { code } = await wx.login()
     const res = await api.wechatLogin(code)
     if (res.bound && res.username) {
       api.setCurrentUser(res.username)
       this.setData({ selectedUser: res.username })
       this.loadUsers()
       this.loadAll(res.username)
       return
     }
     // 未绑定，加载用户列表
     this.setData({ wechatOpenid: res.openid })
     this.loadUsers()
     try {
       const unbound = await api.getUnbound()
       if (!unbound || unbound.length === 0) {
         this.setData({ showCreate: true, newUserName: '' })
       } else {
         this.setData({ showBind: true, unboundList: unbound })
       }
     } catch (_) {
       this.setData({ showCreate: true, newUserName: '' })
     }
   } catch (_) {
     // wechatLogin失败（如网络问题），尝试从缓存加载用户
     this.loadUsers()
     const saved = api.getCurrentUser()
     if (saved) {
       this.setData({ selectedUser: saved })
       this.loadAll(saved)
     }
   }
 },

  async loadUsers() {
    try { this.setData({ userList: await api.getUsers() || [] }) } catch (_) {}
  },

  onUserChange(e) {
    const user = this.data.userList[e.detail.value]
    if (user) {
      api.setCurrentUser(user)
      this.setData({ selectedUser: user })
      this.loadAll(user)
    }
  },

  async loadAll(user) {
    this.setData({ loading: true })
    let hasData = false
    try {
      const stats = await api.getStats()
      const totals = stats.totals || {}
      if (totals.total_volume) totals.volK = (totals.total_volume / 1000).toFixed(0)
      if (!(totals.total_workouts || 0)) {
        this.setData({ loading: false, hasData: false })
        return
      }

      // 并发获取：全部训练 + 复合动作历史
      const [allWorkouts, compoundData] = await Promise.all([
        this.retryGetWorkouts(),
        this.fetchCompoundHistory(),
      ])

      // PR 记录
      const prs = (stats.prs || []).filter(p => p.weight_kg > 0)
      const prList = prs.map(p => ({
        name: p.name, weight: p.weight_kg, reps: p.reps, date: p.date,
        category: p.category, tagClass: 'tag ' + (p.category || '').toLowerCase()
      }))

      // 力量曲线
      const strengthLifts = this.buildStrengthLifts(compoundData)

      // 周训练量
      const weeklyVolumes = this.buildWeeklyVolumes(allWorkouts)

      // 训练频率
      const calData = this.buildCalendar(allWorkouts)

      // 推拉腿分布
      const byType = stats.by_type || []
      const maxCat = Math.max(...byType.map(t => t.volume || 0), 1)
      const catBars = byType.map(t => ({
        type: t.type, color: CAT_COLORS[t.type] || '#58a6ff',
        volK: (t.volume / 1000).toFixed(0), pct: (t.volume / maxCat * 100).toFixed(0)
      }))

      // 上次训练
      let lastWorkout = null
      try {
        const lw = await api.getLastWorkout()
        if (lw && lw.sets) {
          const exMap = {}
          for (const s of lw.sets) {
            const en = s.exercise || ''
            if (!exMap[en]) exMap[en] = { exName: en, sets: [] }
            exMap[en].sets.push({ id: s.id, set_number: s.set_number, weight_kg: s.weight_kg, reps: s.reps })
          }
          const dur = lw.duration_min || 0
          lastWorkout = { date: lw.date, type: lw.type || '', duration: dur, exercises: Object.values(exMap) }
          this.setData({ lastWorkoutStr: lw.date + ' · ' + (lw.type || '') + ' · ' + dur + '分' })
        }
      } catch (_) {}

      // 亮点
      const highlights = this.computeHighlights(stats.recent || [], weeklyVolumes)

      hasData = true
      this.setData({
        loading: false, hasData: true,
        totals, prList, strengthLifts, weeklyVolumes,
        calGrid: calData.grid, calMonths: calData.months,
        catBars, lastWorkout, highlights
      })
    } catch (e) {
      console.error('loadAll失败:', e)
      this.setData({ loading: false, hasData: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  // ── ③ 力量曲线 ───────────────────────────
  async fetchCompoundHistory() {
    const map = {}
    try {
      const exs = await api.getExercises()
      if (!exs || !exs.length) return map
      const batch = []
      for (const cn of COMPOUND_NAMES) {
        const found = exs.find(e => e.name === cn)
        if (found) batch.push({ id: found.id, name: found.name })
      }
      if (!batch.length) return map
      // 逐个请求，自动重试1次
      for (const item of batch) {
        for (let attempt = 0; attempt < 2; attempt++) {
          try {
            const sets = await api.getSetHistory(item.id)
            if (sets && sets.length) { map[item.id] = sets; break }
          } catch (_) {
            if (attempt === 1) break // 最后一次失败就算了
            await new Promise(r => setTimeout(r, 500)) // 等500ms重试
          }
        }
      }
    } catch (_) {}
    return map
  },

  async retryGetWorkouts() {
    for (let i = 0; i < 2; i++) {
      try {
        const data = await api.getWorkouts(200)
        if (data) return data
      } catch (_) {
        if (i === 0) await new Promise(r => setTimeout(r, 500))
      }
    }
    return []
  },

  buildStrengthLifts(compoundData) {
    const lifts = []
    for (const [exId, sets] of Object.entries(compoundData)) {
      if (!sets.length) continue
      const name = sets[0].name

      const byDate = {}
      for (const s of sets) {
        const d = s.date
        if (!byDate[d] || s.weight_kg > byDate[d].weight) {
          byDate[d] = { weight: s.weight_kg, reps: s.reps }
        } else if (s.weight_kg === byDate[d].weight && s.reps > byDate[d].reps) {
          // Same max weight, pick the set with more reps
          byDate[d] = { weight: s.weight_kg, reps: s.reps }
        }
      }

      const dates = Object.keys(byDate).sort()
      if (dates.length < 2) continue

      const dataPts = dates.map(d => ({ date: d, ...byDate[d] }))
      const maxWt = Math.max(...dataPts.map(p => p.weight))
      const minWt = Math.min(...dataPts.map(p => p.weight))
      const range = Math.max(maxWt - minWt, 1)

      // Sample to max ~15 bars so phone screen doesn't get crammed
      const MAX_BARS = 15
      let sampled = dataPts
      if (dataPts.length > MAX_BARS) {
        const step = (dataPts.length - 1) / (MAX_BARS - 1)
        sampled = []
        for (let i = 0; i < MAX_BARS; i++) {
          sampled.push(dataPts[Math.round(i * step)])
        }
      }

      const bars = sampled.map(p => ({
        date: p.date.slice(5),
        pct: Math.max(((p.weight - minWt) / range * 70 + 10), 5),
        weight: p.weight, reps: p.reps
      }))

      const latest = dataPts[dataPts.length - 1]

      lifts.push({ name, bars, latest, maxWt, minWt })
    }
    return lifts
  },

  // ── ④ 周训练量 ───────────────────────────
  buildWeeklyVolumes(workouts) {
    const weeks = {}
    for (const w of workouts) {
      const dt = new Date(w.date)
      const day = dt.getDay()
      const diff = dt.getDate() - (day === 0 ? 6 : day - 1)
      const mon = new Date(dt)
      mon.setDate(diff)
      const key = mon.toISOString().slice(0, 10)
      if (!weeks[key]) weeks[key] = { week: key, volume: 0 }
      weeks[key].volume += w.total_volume || 0
    }
    let vols = Object.values(weeks).sort((a, b) => a.week.localeCompare(b.week))
    // Last 12 weeks
    vols = vols.slice(-12)
    const maxV = Math.max(...vols.map(v => v.volume), 1)
    return vols.map(v => ({
      label: v.week.slice(5), // MM-DD
      volK: (v.volume / 1000).toFixed(0),
      pct: Math.max((v.volume / maxV * 100), 3)
    }))
  },

  // ── ⑤ 训练频率热力图 ───────────────────────
  buildCalendar(workouts) {
    const today = new Date()
    const year = today.getFullYear()
    const month = today.getMonth() // 0-indexed

    // Build set of workout dates
    const workoutDates = new Set()
    for (const w of workouts) {
      workoutDates.add(w.date)
    }

    // Generate current month grid
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const firstDay = new Date(year, month, 1).getDay() // 0=Sun
    const monthLabel = year + '年' + (month + 1) + '月'

    const grid = []
    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
      grid.push({ empty: true })
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      grid.push({
        day: d, date: dateStr,
        hasWorkout: workoutDates.has(dateStr),
        isToday: dateStr === today.toISOString().slice(0, 10)
      })
    }

    return { grid, months: [monthLabel] }
  },

  // ── ⑧ 亮点 ──────────────────────────────
  computeHighlights(workouts, weekly) {
    const h = []
    if (!workouts || !workouts.length) return h
    const best = workouts.reduce((a, b) => (a.volume || 0) > (b.volume || 0) ? a : b)
    if (best.volume) h.push({ type: 'best', text: '最佳训练 ' + best.date + ' — ' + best.volume + 'kg (' + best.sets + '组)' })
    const last = workouts[0]
    if (last) h.push({ type: 'last', text: '最近训练 ' + last.date + ' · ' + (last.type || '') + ' · ' + (last.volume || 0) + 'kg' })
    if (weekly && weekly.length >= 2) {
      const cur = weekly[weekly.length - 1], prev = weekly[weekly.length - 2]
      if (cur && prev && prev.volK > 0) {
        const curV = parseInt(cur.volK) * 1000, prevV = parseInt(prev.volK) * 1000
        const diff = ((curV - prevV) / prevV * 100).toFixed(0)
        h.push({ type: 'trend', text: '本周训练量 ' + curV + 'kg — 较上周' + (diff > 0 ? '↑' : '↓') + Math.abs(diff) + '%' })
      }
    }
    return h
  },

  // ── 用户绑定 ─────────────────────────────
  onBindExisting() { this.setData({ showBind: false, showBindPicker: true }) },
  onConfirmBind(e) { this.doBind(e.currentTarget.dataset.user) },
  async doBind(username) {
    wx.showLoading({ title: '绑定中...' })
    try {
      await api.wechatBind(this.data.wechatOpenid, username)
      wx.hideLoading()
      api.setCurrentUser(username)
      this.setData({ selectedUser: username, showBindPicker: false, showBind: false })
      this.loadAll(username)
      wx.showToast({ title: '绑定成功', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: e.message || '绑定失败', icon: 'error' })
    }
  },
  onCancelBind() { this.setData({ showBind: false }) },
  onCancelBindPicker() { this.setData({ showBindPicker: false }) },
  onCreateUser() { this.setData({ showBind: false, showCreate: true, newUserName: '' }) },
  async onConfirmCreate() {
    const name = this.data.newUserName.trim()
    if (!name) { wx.showToast({ title: '请输入用户名', icon: 'none' }); return }
    wx.showLoading({ title: '创建中...' })
    try {
      await api.wechatCreate(this.data.wechatOpenid, name)
      wx.hideLoading()
      api.setCurrentUser(name)
      this.setData({ selectedUser: name, showCreate: false })
      const users = await api.getUsers()
      this.setData({ userList: users || [] })
      // 新用户直接跳转训练页记录第一次训练
      wx.showToast({ title: '创建成功，开始你的第一次训练吧！', icon: 'success', duration: 2000 })
      setTimeout(async () => {
        try {
          const today = new Date()
          const dateStr = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0')
          const dow = today.getDay()
          const idx = dow === 0 ? 6 : dow - 1
          const weekTypes = ['Push', 'Pull', 'Legs', 'Push', 'Pull', 'Legs', 'Rest']
          const todayType = weekTypes[idx] || 'Push'
          const workout = await api.startWorkout({ date: dateStr, type: todayType, owner: api.getCurrentUser() })
          wx.navigateTo({ url: '/pages/workout/workout?wid=' + workout.id })
        } catch (e) {
          wx.showToast({ title: e.message || '创建失败', icon: 'error' })
        }
      }, 1500)
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: e.message || '创建失败', icon: 'error' })
    }
  },
  onCancelCreate() { this.setData({ showCreate: false }) },

  // ── 首次训练引导 ─────────────────────────
  async onStartFirstWorkout() {
    wx.showLoading({ title: '创建训练...' })
    try {
      const today = new Date()
      const dateStr = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0')
      const dow = today.getDay()
      const idx = dow === 0 ? 6 : dow - 1
      const weekTypes = ['Push', 'Pull', 'Legs', 'Push', 'Pull', 'Legs', 'Rest']
      const todayType = weekTypes[idx] || 'Push'

      const workout = await api.startWorkout({
        date: dateStr, type: todayType, owner: api.getCurrentUser()
      })
      wx.hideLoading()
      wx.navigateTo({ url: '/pages/workout/workout?wid=' + workout.id })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: e.message || '创建失败', icon: 'error' })
    }
  },
})
