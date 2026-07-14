const api = require('../../utils/api')

const CAT_COLORS = { Push: '#f85149', Pull: '#d29922', Legs: '#3fb950' }
const EX_COLORS = ['#58a6ff', '#bc8cff', '#39d2c0', '#f5c342', '#f85149', '#3fb950', '#d29922', '#1f6feb', '#da3633', '#238636']

const COMPOUND_NAMES = ['杠铃深蹲', '杠铃卧推', '罗马尼亚硬拉', '硬拉', '助力引体向上', '高位下拉', '低位划船']

// ── 动作知识库 ──
const EXERCISE_INFO = {
  '杠铃卧推': {
    muscles: '胸大肌（整体）· 三角肌前束 · 肱三头肌',
    notes: '肩胛骨全程收紧贴凳 · 杠铃触胸即起 · 手腕中立不后翻 · 脚踩实地面'
  },
  '哑铃上斜卧推': {
    muscles: '胸大肌（上胸）· 三角肌前束 · 肱三头肌',
    notes: '凳角30-45° · 哑铃下落至大小臂90° · 顶点挤压胸 · 肘不过度外展'
  },
  '侧平举': {
    muscles: '三角肌（中束为主）· 冈上肌',
    notes: '身体微前倾稳住肩胛 · 肘微屈固定角度 · 手不高于肘 · 不要借力甩'
  },
  '绳索下压': {
    muscles: '肱三头肌（外侧头+长头）',
    notes: '大臂贴肋不动 · 下压至手臂伸直 · 缓慢回放控制 · 身体勿前后晃'
  },
  '双杠臂屈伸(助力)': {
    muscles: '胸大肌（下胸）· 肱三头肌 · 三角肌前束',
    notes: '含胸微前倾练胸 · 直身上下练三头 · 下落勿过低伤肩 · 肘不内夹'
  },
  '俯卧撑': {
    muscles: '胸大肌 · 三角肌前束 · 肱三头肌 · 核心',
    notes: '身体成直线不塌腰 · 手略宽于肩 · 下落至胸触地 · 肘45°夹'
  },
  '高位下拉': {
    muscles: '背阔肌（宽度）· 肱二头肌 · 大圆肌',
    notes: '肩胛下沉启动 · 拉至锁骨位 · 肘垂直向下画弧 · 躯干微后倾不动晃'
  },
  '低位划船': {
    muscles: '背阔肌（厚度）· 菱形肌 · 斜方肌中束 · 肱二头肌',
    notes: '肩胛后缩启动 · 拉至腹部 · 肘贴肋向后 · 顶峰夹背1秒'
  },
  '面拉': {
    muscles: '三角肌后束 · 冈下肌 · 小圆肌 · 菱形肌',
    notes: '拉至眼前方 · 肘高过腕 · 末端外旋肩 · 轻重量高次数'
  },
  '哑铃弯举': {
    muscles: '肱二头肌（长头+短头）· 肱肌',
    notes: '大臂贴肋不动 · 腕中立 · 全幅度伸到底 · 勿甩腰借力'
  },
  '直臂下压': {
    muscles: '背阔肌（下背）· 大圆肌 · 胸大肌下束（辅助）',
    notes: '肘微屈固定角度 · 身体微前倾 · 下压至大腿侧 · 放回可控'
  },
  '反向蝴蝶机': {
    muscles: '三角肌后束 · 冈下肌 · 小圆肌 · 菱形肌',
    notes: '肩胛打开前伸 · 后拉至与肩平 · 肘微屈 · 勿用背夹代偿'
  },
  '杠铃深蹲': {
    muscles: '股四头肌 · 臀大肌 · 腘绳肌 · 竖脊肌 · 核心',
    notes: '杠铃高杠位 · 膝随脚尖方向 · 核心绷紧不松 · 大腿与地面平行或更低 · 踝活动度不够可垫片'
  },
  '腿屈伸': {
    muscles: '股四头肌（整体，重点股内侧肌）',
    notes: '坐垫调整使膝对准转轴 · 全幅度慢放 · 顶峰挤压 · 勿甩腿借力'
  },
  '保加利亚分腿蹲': {
    muscles: '股四头肌 · 臀大肌 · 腘绳肌 · 核心',
    notes: '后脚垫高 · 躯干微前倾 · 前膝不超脚尖 · 后膝接近地面 · 单边完成再换'
  },
  '腿弯举': {
    muscles: '腘绳肌（股二头肌）· 腓肠肌',
    notes: '髋贴紧凳面 · 全幅度慢放 · 顶峰挤压 · 勿用爆发力甩'
  },
  '提踵': {
    muscles: '腓肠肌 · 比目鱼肌',
    notes: '站姿练腓肠肌 · 坐姿练比目鱼肌 · 全幅度 · 顶峰挤压2秒 · 高次数'
  },
  '相扑深蹲': {
    muscles: '大腿内收肌 · 臀大肌 · 股四头肌',
    notes: '站距宽于肩 · 脚尖外展45° · 膝随脚尖方向 · 上身直立 · 蹲到底'
  },
  '负重臀推': {
    muscles: '臀大肌（主打）· 腘绳肌 · 核心',
    notes: '肩胛骨靠凳 · 髋顶至肩-膝成直线 · 顶峰挤压 · 下放不碰地'
  },
  '助力引体向上': {
    muscles: '背阔肌 · 肱二头肌 · 大圆肌 · 斜方肌',
    notes: '宽握练宽度 · 反握练二头 · 下放到底 · 肩胛主动收紧'
  },
  '罗马尼亚硬拉': {
    muscles: '腘绳肌 · 臀大肌 · 竖脊肌 · 核心',
    notes: '髋向后推启动 · 膝微屈固定 · 杠铃贴腿下放至小腿中 · 腘绳感为主 · 勿弓腰'
  },
  '硬拉': {
    muscles: '全身后侧链：腘绳肌 · 臀大肌 · 竖脊肌 · 背阔肌 · 前臂',
    notes: '杠铃贴胫骨 · 背收紧挺胸 · 髋和肩同步起 · 勿弓腰 · 全程核心绷紧'
  },
}

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
    showExDetail: false,
    exDetailData: null,
    highlights: [],
    strengthChartFailed: false,
    prCollapsed: true,
    calPopup: null, calPopupData: null,
    strengthTab: 'Push',
  },

  async onShow() {
    // 每次打开都调微信登录
    this.loadUsers()
    this.setData({ loading: true })
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
      const calData = this.buildCalendar(allWorkouts)

      const byType = stats.by_type || []
      const maxCat = Math.max(...byType.map(t => t.volume || 0), 1)
      const catBars = byType.map(t => ({
        type: t.type, color: CAT_COLORS[t.type] || '#58a6ff',
        volK: (t.volume / 1000).toFixed(0), pct: (t.volume / maxCat * 100).toFixed(0)
      }))

      let lastWorkout = null
      let lastWorkoutStr = ''
      try {
        const lw = await api.getLastWorkout()
        if (lw && lw.sets) {
          const exMap = {}
          for (const s of lw.sets) {
            const en = s.exercise || ''
            if (!exMap[en]) exMap[en] = { exName: en, sets: [], minId: s.id }
            exMap[en].sets.push({ id: s.id, set_number: s.set_number, weight_kg: s.weight_kg, reps: s.reps })
            if (s.id < exMap[en].minId) exMap[en].minId = s.id
          }
          const dur = lw.duration_min
          const durNum = (dur === 'NULL' || dur === null || dur === undefined) ? 0 : dur
          const exercises = Object.values(exMap).sort((a, b) => a.minId - b.minId)
          lastWorkout = { date: lw.date, type: lw.type || '', duration: durNum, exercises }
          lastWorkoutStr = lw.date + ' · ' + (lw.type || '') + ' · ' + durNum + '分'
        }
      } catch (_) {}

      const highlights = this.computeHighlights(stats.recent || [], weeklyVolumes)

      hasData = true
      this.setData({
        loading: false, hasData: true,
        totals, prList, displayPrList, strengthLifts, strengthDisplayLifts, weeklyVolumes,
        calGrid: calData.grid, calMonths: calData.months,
        catBars, lastWorkout, lastWorkoutStr, highlights,
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

  buildCalendar(workouts) {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()
    const todayLocal = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0')
    const workoutByDate = {}
    for (const w of workouts) workoutByDate[w.date] = w
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
    return { grid, months: [monthLabel] }
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
  onExNameTap(e) {
    const name = e.currentTarget.dataset.exname
    const info = EXERCISE_INFO[name]
    if (!info) return  // 没有知识库的动作不弹
    this.setData({ showExDetail: true, exDetailData: { name, ...info } })
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
})
