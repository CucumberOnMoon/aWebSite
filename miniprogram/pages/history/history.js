const api = require('../../utils/api')
const TYPE_CN = { Push: '推', Pull: '拉', Legs: '腿' }

Page({
  data: {
    list: [],
    loading: true,
    calPopup: null, calPopupData: null,
    userList: [],
    selectedUser: '',
    showUserList: false,
    todayPlan: null,
    todayDone: false,
  },

  onShow() {
    this.loadUsers()
    this.load()
    this.loadTodayPlan()
  },

  // 今日计划：练完（today.done）就整块不显示
  async loadTodayPlan() {
    try {
      const dow = new Date().getDay()
      const plan = await api.getPlan(dow)
      const today = (plan && plan.today) || null
      const dayPlan = (plan && plan.days || []).find(d => d.dow === dow) || null
      this.setData({ todayPlan: dayPlan, todayDone: !!(today && today.done) })
    } catch (_) {
      this.setData({ todayPlan: null, todayDone: false })
    }
  },

  goPlan() {
    wx.navigateTo({ url: '/pages/plan/plan' })
  },

  async loadUsers() {
    try {
      const users = await api.getUsers()
      this.setData({
        userList: users || [],
        selectedUser: api.getCurrentUser() || api.MAIN_OWNER,
      })
    } catch (_) {}
  },

  // ── 用户下拉（与首页一致）──────────────
  noop() {},
  toggleUserList() { this.setData({ showUserList: !this.data.showUserList }) },
  closeUserList() { this.setData({ showUserList: false }) },
  onPickUser(e) {
    const user = e.currentTarget.dataset.user
    this.setData({ showUserList: false })
    if (!user || user === this.data.selectedUser) return
    api.setCurrentUser(user)
    this.setData({ selectedUser: user })
    this.load()
    this.loadTodayPlan()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const raw = await api.getWorkouts(30)
      const list = (raw || []).map(w => ({
        id: w.id, date: w.date || '',
        type: (w.type || '').toLowerCase(),
        typeLabel: TYPE_CN[w.type] || w.type || '',
        typeCn: TYPE_CN[w.type] || w.type || '',
        duration: w.duration_min ? w.duration_min + '分钟' : '-',
        sets: w.sets || 0, volume: w.total_volume || 0
      }))
      this.setData({ list, loading: false })
    } catch (_) {
      this.setData({ loading: false })
    }
  },

  async onHistTap(e) {
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
          const cn = s.exercise_cn || ''
          const key = en || cn
          if (!exMap[key]) exMap[key] = { exName: cn || en, exercise: en, sets: [], minId: s.id }
          exMap[key].sets.push({ id: s.id, set_number: s.set_number, weight_kg: s.weight_kg, reps: s.reps })
          if (s.id < exMap[key].minId) exMap[key].minId = s.id
        }
        const exercises = Object.values(exMap).sort((a, b) => a.minId - b.minId)
        this.setData({ calPopupData: {
          date: data.date, type: TYPE_CN[data.type] || data.type, duration: data.duration_min,
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
