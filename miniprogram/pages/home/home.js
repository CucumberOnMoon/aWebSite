const api = require('../../utils/api')

const CAT_COLORS = { Push: '#f85149', Pull: '#d29922', Legs: '#3fb950' }
const EX_COLORS = ['#58a6ff', '#bc8cff', '#39d2c0', '#f5c342', '#f85149', '#3fb950', '#d29922', '#1f6feb', '#da3633', '#238636']

function groupByWeek(workouts) {
  const weeks = {}
  for (const w of workouts) {
    const dt = new Date(w.date)
    const day = dt.getDay()
    const diff = dt.getDate() - (day === 0 ? 6 : day - 1)
    const mon = new Date(dt)
    mon.setDate(diff)
    const key = mon.toISOString().slice(0, 10)
    if (!weeks[key]) weeks[key] = { week: key, volume: 0, sets: 0, sessions: 0 }
    weeks[key].volume += w.total_volume || 0
    weeks[key].sets += w.sets || 0
    weeks[key].sessions += 1
  }
  return Object.values(weeks).sort((a, b) => a.week.localeCompare(b.week))
}

Page({
  data: {
    loading: false,
    userList: [],
    selectedUser: '',
    hasData: false,
    totals: {},
    highlights: [],
    weeklyBars: [],
    catBars: [],
    exBars: [],
    recent: [],
    filteredRecent: [],
    tabFilter: 'All'
  },

  onShow() {
    this.loadUsers()
    const saved = api.getCurrentUser()
    if (saved) {
      this.setData({ selectedUser: saved })
      this.loadStats(saved)
    }
  },

  async loadUsers() {
    try {
      const users = await api.getUsers()
      this.setData({ userList: users || [] })
    } catch (_) {}
  },

  onUserChange(e) {
    const idx = e.detail.value
    const user = this.data.userList[idx]
    if (user) {
      api.setCurrentUser(user)
      this.setData({ selectedUser: user })
      this.loadStats(user)
    }
  },

  async loadStats(user) {
    this.setData({ loading: true })
    try {
      const stats = await api.getStats()
      const totals = stats.totals || {}
      if (!(totals.total_workouts || 0)) {
        this.setData({ loading: false, hasData: false })
        return
      }

      // 最近训练作为周趋势数据
      let allSessions = (stats.recent || []).slice().reverse().map(r => ({
        date: r.date, total_volume: r.volume, sets: r.sets, type: r.type
      }))

      let weekly = []
      try {
        const more = await api.getWorkouts(100)
        if (more && more.length) weekly = groupByWeek(more)
      } catch (_) {
        weekly = groupByWeek(allSessions.length > 3 ? allSessions : [])
      }

      const maxVol = Math.max(...weekly.map(w => w.volume), 1)
      const weeklyBars = weekly.slice(-10).map(w => ({
        label: w.week.slice(5), volK: (w.volume / 1000).toFixed(0),
        pct: (w.volume / maxVol * 100).toFixed(0)
      }))

      const byType = stats.by_type || []
      const maxCat = Math.max(...byType.map(t => t.volume || 0), 1)
      const catBars = byType.map(t => ({
        type: t.type, color: CAT_COLORS[t.type] || '#58a6ff',
        volK: (t.volume / 1000).toFixed(0), pct: (t.volume / maxCat * 100).toFixed(0)
      }))

      const exs = (stats.exercises || []).slice(0, 10)
      const maxEx = Math.max(...exs.map(e => e.total_volume || 0), 1)
      const exBars = exs.map((e, i) => ({
        name: e.name.length > 6 ? e.name.slice(0, 6) + '..' : e.name,
        volK: (e.total_volume / 1000).toFixed(0), pct: (e.total_volume / maxEx * 100).toFixed(0),
        color: EX_COLORS[i % EX_COLORS.length]
      }))

      const recent = (stats.recent || []).map(r => ({
        ...r,
        typeL: ((r.type || '')[0] || ''),
        tagClass: 'tag ' + (r.type || '').toLowerCase(),
        duration: r.duration_min || 0
      }))

      const highlights = this.computeHighlights(stats.recent || [], weekly)

      this.setData({
        loading: false, hasData: true,
        totals, highlights, weeklyBars, catBars, exBars,
        recent, filteredRecent: recent, tabFilter: 'All'
      })
    } catch (e) {
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  computeHighlights(workouts, weekly) {
    const h = []
    if (!workouts.length) return h
    const best = workouts.reduce((a, b) => (a.volume || 0) > (b.volume || 0) ? a : b)
    if (best.volume) h.push({ type: 'best', text: '最佳训练 ' + best.date + ' — ' + best.volume + 'kg (' + best.sets + '组)' })
    const last = workouts[0]
    if (last) h.push({ type: 'last', text: '最近训练 ' + last.date + ' · ' + (last.type || '') + ' · ' + (last.volume || 0) + 'kg' })
    if (weekly.length >= 2) {
      const cur = weekly[weekly.length - 1], prev = weekly[weekly.length - 2]
      if (cur && prev && prev.volume > 0) {
        const diff = ((cur.volume - prev.volume) / prev.volume * 100).toFixed(0)
        h.push({ type: 'trend', text: '本周训练量 ' + cur.volume + 'kg (' + cur.sessions + '次) — 较上周' + (diff > 0 ? '↑' : '↓') + Math.abs(diff) + '%' })
      }
    }
    return h
  },

  onTab(e) {
    const filter = e.currentTarget.dataset.tab
    const filtered = filter === 'All' ? this.data.recent : this.data.recent.filter(r => r.type === filter)
    this.setData({ tabFilter: filter, filteredRecent: filtered })
  }
})
