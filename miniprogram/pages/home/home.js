const api = require('../../utils/api')
const { EXERCISE_INFO } = require('../../utils/exercises')

const CAT_COLORS = { Push: '#f85149', Pull: '#d29922', Legs: '#3fb950' }
const EX_COLORS = ['#58a6ff', '#bc8cff', '#39d2c0', '#f5c342', '#f85149', '#3fb950', '#d29922', '#1f6feb', '#da3633', '#238636']

const COMPOUND_NAMES = ['杠铃深蹲', '杠铃卧推', '罗马尼亚硬拉', '硬拉', '助力引体向上', '高位下拉', '低位划船']

Page({
  data: {
    loading: false,
    wxDone: false,
    userList: [],
    selectedUser: '',
    boundUser: '',
    hasData: false,
    showBind: false, showBindPicker: false, showCreate: false,
    wechatOpenid: '', unboundList: [], newUserName: '',

    totals: {},
    prList: [],
    strengthLifts: [],
    weeklyVolumes: [],
    calGrid: [], calMonths: [],
    catBars: [],
    lastWorkout: null,
    lastWorkoutStr: '',
    lastWorkoutOffset: 0,
    lastWorkoutMore: true,
    showExDetail: false,
    exDetailData: null,
    highlights: [],
    strengthChartFailed: false,
    prCollapsed: true,
    calPopup: null, calPopupData: null,
    calYear: 0, calMonth: 0,
    strengthTab: 'Push',
    appVersion: '1.8.1',
    // Timer
    timerActive: false,
    timerRemaining: 0,
    timerEnd: 0,
  },

  async onShow() {
    // 每次打开都调微信登录
    this.loadUsers()
    this.setData({ loading: true })

    // Check if timer expired while we were away
    this.checkTimerExpired()

    try {
      const { code } = await wx.login()
      const res = await api.wechatLogin(code)
      if (res && res.bound && res.username) {
        api.setCurrentUser(res.username)
        this.setData({ selectedUser: res.username, boundUser: res.username, loading: false })
        this.loadAll(res.username)
      } else if (res && res.openid) {
        this.setData({ wechatOpenid: res.openid, loading: false, showBind: true })
        this.loadUsers()
        // 后台加载未绑定用户列表
        api.getUnbound().then(list => {
          if (list && list.length > 0) this.setData({ unboundList: list })
        }).catch(() => {})
      } else {
        this.setData({ loading: false, showBind: true })
        this.loadUsers()
        api.getUnbound().then(list => {
          if (list && list.length > 0) this.setData({ unboundList: list })
        }).catch(() => {})
      }
    } catch (_) {
      // 微信登录失败，弹绑定框让用户操作
      this.loadUsers()
      this.setData({ showBind: true, loading: false })
      api.getUnbound().then(list => {
        if (list && list.length > 0) this.setData({ unboundList: list })
      }).catch(() => {})
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

      const [allWorkouts, compoundData] = await Promise.all([
        this.retryGetWorkouts(),
        this.fetchCompoundHistory(),
      ])

      const prs = (stats.prs || []).filter(p => p.weight_kg > 0)
      const prList = prs.map(p => ({
        name: p.name, weight: p.weight_kg, reps: p.reps, date: p.date,
        category: p.category, tagClass: 'tag ' + (p.category || '').toLowerCase()
      }))
      const displayPrList = prList.slice(0, 5)

      const strengthLifts = this.buildStrengthLifts(compoundData)
      const strengthDisplayLifts = this.getStrengthByTab(strengthLifts, 'Push')
      const weeklyVolumes = this.buildWeeklyVolumes(allWorkouts)
      const now = new Date()
      const calData = this.buildCalendar(allWorkouts, now.getFullYear(), now.getMonth())

      const byType = stats.by_type || []
      const maxCat = Math.max(...byType.map(t => t.volume || 0), 1)
      const catBars = byType.map(t => ({
        type: t.type, color: CAT_COLORS[t.type] || '#58a6ff',
        volK: (t.volume / 1000).toFixed(0), pct: (t.volume / maxCat * 100).toFixed(0)
      }))

      let lastWorkout = null
      let lastWorkoutStr = ''
      try {
        const lw = await api.getLastWorkout(0)
        if (lw && lw.sets) {
          const formatted = this.formatLastWorkout(lw)
          lastWorkout = formatted.data
          lastWorkoutStr = formatted.str
        }
      } catch (_) {}

      const highlights = this.computeHighlights(stats.recent || [], weeklyVolumes)

      // Init cache with offset 0 workout
      if (lastWorkout) {
        this._workoutCache = { 0: { data: lastWorkout, str: lastWorkoutStr } }
      }

      hasData = true
      this.setData({
        loading: false, hasData: true,
        totals, prList, displayPrList, strengthLifts, strengthDisplayLifts, weeklyVolumes,
        calGrid: calData.grid, calMonths: calData.months,
        calYear: calData.year, calMonth: calData.month,
        catBars, lastWorkout, lastWorkoutStr, highlights,
        lastWorkoutOffset: 0, lastWorkoutMore: true,
        strengthChartFailed: !strengthLifts.length && this._compoundFetchFailed,
      })
    } catch (e) {
      console.error('loadAll失败:', e)
      this.setData({ loading: false, hasData: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  async fetchCompoundHistory() {
    const map = {}
    this._compoundFetchFailed = false
    try {
      let exs = null
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          exs = await api.getExercises()
          if (exs && exs.length) break
        } catch (_) {
          this._compoundFetchFailed = true
          if (attempt === 0) await new Promise(r => setTimeout(r, 500))
        }
      }
      if (!exs || !exs.length) return map
      const batch = []
      for (const cn of COMPOUND_NAMES) {
        const found = exs.find(e => e.name === cn)
        if (found) batch.push({ id: found.id, name: found.name })
      }
      if (!batch.length) return map
      for (const item of batch) {
        for (let attempt = 0; attempt < 2; attempt++) {
          try {
            const sets = await api.getSetHistory(item.id)
            if (sets && sets.length) { map[item.id] = sets; break }
          } catch (_) {
            this._compoundFetchFailed = true
            if (attempt === 1) break
            await new Promise(r => setTimeout(r, 500))
          }
        }
      }
    } catch (_) { this._compoundFetchFailed = true }
    return map
  },

  async retryStrengthChart() {
    this.setData({ strengthChartFailed: false, loading: true })
    const compoundData = await this.fetchCompoundHistory()
    const strengthLifts = this.buildStrengthLifts(compoundData)
    const strengthDisplayLifts = this.getStrengthByTab(strengthLifts, 'Push')
    this.setData({ strengthLifts, strengthDisplayLifts, loading: false })
    if (!strengthLifts.length && this._compoundFetchFailed) {
      this.setData({ strengthChartFailed: true })
    }
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
      const category = sets[0].category || ''
      const color = CAT_COLORS[category] || '#58a6ff'
      const byDate = {}
      for (const s of sets) {
        const d = s.date
        if (!byDate[d] || s.weight_kg > byDate[d].weight) {
          byDate[d] = { weight: s.weight_kg, reps: s.reps }
        } else if (s.weight_kg === byDate[d].weight && s.reps > byDate[d].reps) {
          byDate[d] = { weight: s.weight_kg, reps: s.reps }
        }
      }
      const dates = Object.keys(byDate).sort()
      if (dates.length < 2) continue
      const dataPts = dates.map(d => ({ date: d, ...byDate[d] }))
      const maxWt = Math.max(...dataPts.map(p => p.weight))
      const minWt = Math.min(...dataPts.map(p => p.weight))
      const range = Math.max(maxWt - minWt, 1)
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
      lifts.push({ name, bars, latest, maxWt, minWt, color, category })
    }
    return lifts
  },

  getStrengthByTab(alls, tab) {
    return alls.filter(l => l.category === tab) || []
  },

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
    vols = vols.slice(-12)
    const maxV = Math.max(...vols.map(v => v.volume), 1)
    return vols.map(v => ({
      label: v.week.slice(5),
      volK: (v.volume / 1000).toFixed(0),
      pct: Math.max((v.volume / maxV * 100), 3)
    }))
  },

  buildCalendar(workouts, year, month) {
    const now = new Date()
    const todayLocal = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0')
    const workoutByDate = {}
    if (workouts) {
      for (const w of workouts) workoutByDate[w.date] = w
    } else {
      workouts = this._allWorkouts || []
      for (const w of workouts) workoutByDate[w.date] = w
    }
    this._allWorkouts = workouts
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const firstDay = new Date(year, month, 1).getDay()
    const monthLabel = year + '年' + (month + 1) + '月'
    const grid = []
    for (let i = 0; i < firstDay; i++) grid.push({ empty: true })
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      const w = workoutByDate[dateStr]
      grid.push({
        day: d, date: dateStr,
        hasWorkout: !!w,
        isToday: dateStr === todayLocal,
        wtype: w ? w.type : '',
        wid: w ? w.id : null,
      })
    }
    return { grid, months: [monthLabel], year, month }
  },

  onCalPrevMonth() {
    let y = this.data.calYear, m = this.data.calMonth
    m--
    if (m < 0) { m = 11; y-- }
    const calData = this.buildCalendar(null, y, m)
    this.setData({ calGrid: calData.grid, calMonths: calData.months, calYear: calData.year, calMonth: calData.month })
  },

  onCalNextMonth() {
    let y = this.data.calYear, m = this.data.calMonth
    m++
    if (m > 11) { m = 0; y++ }
    const calData = this.buildCalendar(null, y, m)
    this.setData({ calGrid: calData.grid, calMonths: calData.months, calYear: calData.year, calMonth: calData.month })
  },

  // Calendar touch swipe
  _calTouchX: 0,
  onCalTouchStart(e) {
    this._calTouchX = e.touches[0].clientX
  },
  onCalTouchEnd(e) {
    const dx = e.changedTouches[0].clientX - (this._calTouchX || 0)
    if (Math.abs(dx) > 50) {
      if (dx > 0) this.onCalPrevMonth()
      else this.onCalNextMonth()
    }
  },

  // ── 上次训练滑动 ──────────────────────────
  formatLastWorkout(lw) {
    const exMap = {}
    for (const s of lw.sets) {
      const en = s.exercise || ''
      const cn = s.exercise_cn || ''
      const key = en || cn
      if (!exMap[key]) exMap[key] = { exName: cn || en, exercise: en, sets: [], minId: s.id }
      exMap[key].sets.push({ id: s.id, set_number: s.set_number, weight_kg: s.weight_kg, reps: s.reps })
      if (s.id < exMap[key].minId) exMap[key].minId = s.id
    }
    const dur = lw.duration_min
    const durNum = (dur === 'NULL' || dur === null || dur === undefined) ? 0 : dur
    const exercises = Object.values(exMap).sort((a, b) => a.minId - b.minId)
    const data = { date: lw.date, type: lw.type || '', duration: durNum, exercises }
    const str = lw.date + ' · ' + (lw.type || '') + ' · ' + durNum + '分'
    return { data, str }
  },

  _workoutCache: {},
  onLastWorkoutPrev() {
    if (this.data.lastWorkoutOffset > 0) {
      this.goToWorkout(this.data.lastWorkoutOffset - 1)
    }
  },
  onLastWorkoutNext() {
    if (this.data.lastWorkoutMore) {
      this.goToWorkout(this.data.lastWorkoutOffset + 1)
    }
  },

  async goToWorkout(offset) {
    let cached = this._workoutCache[offset]
    if (!cached) {
      try {
        const lw = await api.getLastWorkout(offset)
        if (lw && lw.sets) {
          cached = this.formatLastWorkout(lw)
          this._workoutCache[offset] = cached
        }
      } catch (_) {
        if (offset > 0) this.setData({ lastWorkoutMore: false })
        return
      }
    }
    if (cached) {
      this.setData({
        lastWorkoutOffset: offset,
        lastWorkout: cached.data,
        lastWorkoutStr: cached.str,
        lastWorkoutMore: true
      })
    }
  },

  _lastWoTouchX: 0,
  onLastWoTouchStart(e) {
    this._lastWoTouchX = e.touches[0].clientX
  },
  onLastWoTouchEnd(e) {
    const dx = e.changedTouches[0].clientX - (this._lastWoTouchX || 0)
    if (Math.abs(dx) > 50) {
      if (dx > 0) this.onLastWorkoutPrev()
      else this.onLastWorkoutNext()
    }
  },

  computeHighlights(workouts, weekly) {
    const h = []
    // 如果最近训练有summary，直接用它
    if (workouts && workouts.length && workouts[0].summary) {
      h.push({ type: 'summary', text: workouts[0].summary })
      return h
    }
    // 无summary时走旧逻辑
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

  // ── 分享 ──────────────────────────────
  onShareAppMessage() {
    return {
      title: '有没有你 - 健身训练记录',
      path: '/pages/home/home',
    }
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
      this.setData({ selectedUser: username, boundUser: username, showBindPicker: false, showBind: false, wxDone: false })
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
      this.setData({ selectedUser: name, showCreate: false, boundUser: name })
      const users = await api.getUsers()
      this.setData({ userList: users || [] })
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

  // ── 动作详情弹窗 ─────────────────────────
  noop() {},
  async onExNameTap(e) {
    const name = e.currentTarget.dataset.exname
    const engName = e.currentTarget.dataset.engname || name
    const info = EXERCISE_INFO[name] || {}
    let gifUrl = null
    try {
      const res = await api.getExerciseGif(engName)
      if (res && res.gif_url) gifUrl = res.gif_url
    } catch (_) {}
    this.setData({ showExDetail: true, exDetailData: { name, imgName: engName, gif_url: gifUrl, ...info } })
  },
  dismissExDetail() {
    this.setData({ showExDetail: false, exDetailData: null })
  },

  togglePr() {
    const collapsed = !this.data.prCollapsed
    this.setData({
      prCollapsed: collapsed,
      displayPrList: collapsed ? this.data.prList.slice(0, 5) : this.data.prList
    })
  },

  onStrengthTabTap(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ strengthTab: tab, strengthDisplayLifts: this.getStrengthByTab(this.data.strengthLifts, tab) })
  },

  async onCalDayTap(e) {
    const wid = e.currentTarget.dataset.wid
    const wtype = e.currentTarget.dataset.wtype || ''
    if (!wid) return
    this.setData({ calPopup: { type: wtype }, calPopupData: null })
    try {
      const data = await api.getWorkoutSets(wid)
      if (data && data.sets) {
        const exMap = {}
        for (const s of data.sets) {
          const en = s.exercise || ''
          if (!exMap[en]) exMap[en] = { exName: en, sets: [], minId: s.id }
          exMap[en].sets.push({ id: s.id, set_number: s.set_number, weight_kg: s.weight_kg, reps: s.reps })
          if (s.id < exMap[en].minId) exMap[en].minId = s.id
        }
        const exercises = Object.values(exMap).sort((a, b) => a.minId - b.minId)
        this.setData({ calPopupData: {
          date: data.date, type: data.type, duration: data.duration_min,
          exercises
        }})
      }
    } catch (_) {
      this.setData({ calPopup: null, calPopupData: null })
    }
  },

  dismissCalPopup() {
    this.setData({ calPopup: null, calPopupData: null })
  },

  // ── 倒计时 ──────────────────────────────
  TIMER_OPTIONS: [1, 2, 3, 5, 10, 15, 20, 30, 45, 60],

  onTimerTap() {
    var self = this
    wx.showActionSheet({
      itemList: ['1分钟','2分钟','3分钟','5分钟','10分钟','15分钟','20分钟','30分钟','45分钟','60分钟','自定义...'],
      success: function(res) {
        var mins = [1,2,3,5,10,15,20,30,45,60]
        if (res.tapIndex < mins.length) {
          self.startTimer(mins[res.tapIndex])
        } else if (res.tapIndex === mins.length) {
          wx.showModal({
            title: '自定义倒计时',
            editable: true,
            placeholderText: '输入分钟数',
            success: function(r) {
              if (r.confirm && r.content) {
                var n = parseInt(r.content)
                if (n > 0 && n <= 120) self.startTimer(n)
                else wx.showToast({ title: '请输入1-120的整数', icon: 'none' })
              }
            }
          })
        }
      },
      fail: function() {
        wx.showModal({
          title: '选择倒计时',
          editable: true,
          placeholderText: '输入分钟数',
          success: function(r) {
            if (r.confirm && r.content) {
              var n = parseInt(r.content)
              if (n > 0 && n <= 120) self.startTimer(n)
              else wx.showToast({ title: '请输入1-120的整数', icon: 'none' })
            }
          }
        })
      }
    })
  },

  startTimer(minutes) {
    var self = this
    if (this._timerInterval) {
      clearInterval(this._timerInterval)
    }
    // Stop any prior background audio
    try {
      if (self._bgAudio) self._bgAudio.stop()
    } catch(_) {}

    // Request subscribe permission (only prompts first time)
    wx.requestSubscribeMessage({
      tmplIds: ['lsf68_WyUqKrYTi1UhwPpcmbpBjsUZ69EX7-Maw-Tw0'],
      success: function() {},
      fail: function() {},
      complete: function() {
        // Start timer regardless of subscription result
        self._doStartTimer(minutes)
      }
    })
  },

  _doStartTimer(minutes) {
    var self = this
    if (this._timerInterval) {
      clearInterval(this._timerInterval)
    }
    // Stop any prior background audio
    try {
      if (self._bgAudio) self._bgAudio.stop()
    } catch(_) {}

    var now = Date.now()
    var end = now + minutes * 60 * 1000
    this.setData({
      timerActive: true,
      timerRemaining: minutes * 60,
      timerEnd: end,
    })
    // Save end time for onShow check (in case app was killed)
    this._timerEndTime = end
    this._timerMinutes = minutes

    // Start silent background audio to keep JS alive when screen off
    try {
      var bg = wx.getBackgroundAudioManager()
      bg.title = '倒计时'
      bg.epname = '训练倒计时'
      bg.singer = '嘿姆嘿姆'
      bg.src = 'https://avocadocloud.duckdns.org/static/sounds/silent.mp3'
      bg.play()
      self._bgAudio = bg
      // Loop: restart when ended
      bg.onEnded(function() {
        if (self._timerInterval) {
          try { bg.src = 'https://avocadocloud.duckdns.org/static/sounds/silent.mp3'; bg.play() } catch(_) {}
        }
      })
    } catch(e) {
      console.log('bgAudio init failed:', e)
    }

    // Tick every second
    this._timerInterval = setInterval(function() {
      var remaining = Math.max(0, Math.round((end - Date.now()) / 1000))
      if (remaining <= 0) {
        clearInterval(self._timerInterval)
        self._timerInterval = null
        self.setData({ timerActive: false, timerRemaining: 0 })
        self._timerEndTime = 0
        // Play alarm on loop (audible if phone not silent)
        try {
          if (self._bgAudio) {
            self._bgAudio.stop()
            self._bgAudio.src = 'https://avocadocloud.duckdns.org/static/sounds/notice.mp3'
            self._bgAudio.loop = true
            self._bgAudio.play()
          }
        } catch(_) {}
        // Try vibration + modal (works if app is in foreground)
        wx.vibrateLong({ fail: function() {} })
        // Send WeChat notification (works even if screen off)
        try {
          var owner = api.getCurrentUser() || 'howard'
          api.timerNotify(minutes, owner).catch(function() {})
        } catch(_) {}
        wx.showModal({
          title: '⏰ 倒计时结束',
          content: minutes + '分钟计时已到！',
          showCancel: false,
          success: function() {
            // User saw it, stop alarm
            try { if (self._bgAudio) { self._bgAudio.stop(); self._bgAudio = null } } catch(_) {}
          }
        })
        return
      }
      if (remaining % 5 === 0 || remaining <= 10) {
        self.setData({ timerRemaining: remaining })
      }
    }, 1000)
    wx.showToast({ title: '倒计时 ' + minutes + ' 分钟', icon: 'none', duration: 1500 })
  },

  onTimerReset() {
    if (this._timerInterval) {
      clearInterval(this._timerInterval)
      this._timerInterval = null
    }
    try {
      if (this._bgAudio) {
        this._bgAudio.stop()
        this._bgAudio = null
      }
    } catch(_) {}
    this._timerEndTime = 0
    this.setData({ timerActive: false, timerRemaining: 0 })
  },

  // Check when returning to page if timer expired in background
  checkTimerExpired() {
    if (!this._timerEndTime) return
    if (Date.now() >= this._timerEndTime) {
      // Timer expired while we were away
      var mins = this._timerMinutes || 0
      this._timerEndTime = 0
      if (this._timerInterval) {
        clearInterval(this._timerInterval)
        this._timerInterval = null
      }
      this.setData({ timerActive: false, timerRemaining: 0 })
      // Stop silent audio
      try {
        if (this._bgAudio) {
          this._bgAudio.stop()
          this._bgAudio.src = 'https://avocadocloud.duckdns.org/static/sounds/notice.mp3'
          this._bgAudio.loop = true
          this._bgAudio.play()
        }
      } catch(_) {}
      // Vibrate + notify (foreground now, so this works!)
      var self = this
      wx.vibrateLong({ fail: function() {} })
      // Send WeChat notification (may have been missed in background)
      try {
        var owner = api.getCurrentUser() || 'howard'
        api.timerNotify(mins, owner).catch(function() {})
      } catch(_) {}
      wx.showModal({
        title: '⏰ 倒计时结束',
        content: mins + '分钟计时已到！',
        showCancel: false,
        success: function() {
          try { if (self._bgAudio) { self._bgAudio.stop(); self._bgAudio = null } } catch(_) {}
        }
      })
    }
  },
})
