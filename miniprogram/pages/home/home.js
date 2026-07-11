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
    loading: true,
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
    const app = getApp()
    if (!app.globalData.username) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.loadAll()
  },

  async loadAll() {
    this.setData({ loading: true })
    try {
      const stats = await api.getStats()

      const totals = stats.totals || {}
      if (!(totals.total_workouts || 0)) {
        this.setData({ loading: false, hasData: false })
        return
      }

      // 从 stats.recent 生成周趋势数据
      const allSessions = (stats.recent || []).slice().reverse().map(r => ({
        date: r.date, total_volume: r.volume, sets: r.sets, type: r.type
      }))
      // 再补充一些历史数据 - 多取一些 recent 不够用周趋势
      let weekly = []
      try {
        const more = await api.getWorkouts(100)
        if (more && more.length) {
          weekly = groupByWeek(more)
        }
      } catch (_) {
        // workouts 不可用，用 recent 数据
        weekly = groupByWeek(allSessions.length > 3 ? allSessions : [])
      }
      const maxVol = Math.max(...weekly.map(w => w.volume), 1)

      // 每周趋势 bars
      const weeklyBars = weekly.slice(-10).map(w => ({
        label: w.week.slice(5),
        volK: (w.volume / 1000).toFixed(0),
        pct: (w.volume / maxVol * 100).toFixed(0),
        sessions: w.sessions, sets: w.sets
      }))

      // 推拉腿 bars
      const byType = stats.by_type || []
      const maxCat = Math.max(...byType.map(t => t.volume || 0), 1)
      const catBars = byType.map(t => ({
        type: t.type,
        color: CAT_COLORS[t.type] || '#58a6ff',
        volK: (t.volume / 1000).toFixed(0),
        pct: (t.volume / maxCat * 100).toFixed(0),
        sets: t.sets, workouts: t.workouts
      }))

      // 动作详细数据 bars
      const exs = (stats.exercises || []).slice(0, 10)
      const maxEx = Math.max(...exs.map(e => e.total_volume || 0), 1)
      const exBars = exs.map((e, i) => ({
        name: e.name.length > 6 ? e.name.slice(0, 6) + '..' : e.name,
        volK: (e.total_volume / 1000).toFixed(0),
        pct: (e.total_volume / maxEx * 100).toFixed(0),
        color: EX_COLORS[i % EX_COLORS.length],
        fullName: e.name,
        avg: e.avg_weight, sets: e.total_sets
      }))

      // 最近训练
      const recent = (stats.recent || []).map(r => ({
        ...r,
        typeL: ((r.type || '')[0] || '') + ((r.type || '').slice(1) || '').toLowerCase(),
        tagClass: 'tag ' + (r.type || '').toLowerCase(),
        duration: r.duration_min || 0
      }))

      // Highlights
      // Highlights - 用 stats.recent
      const highlights = this.computeHighlights(stats.recent || [], weekly)

      this.setData({
        loading: false, hasData: true,
        totals, highlights,
        weeklyBars, catBars, exBars,
        recent, filteredRecent: recent, tabFilter: 'All'
      })
    } catch (e) {
      if (e.message === 'UNAUTHORIZED') {
        wx.reLaunch({ url: '/pages/login/login' })
        return
      }
      this.setData({ loading: false })
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  computeHighlights(workouts, weekly) {
    const h = []
    if (!workouts.length) return h

    const best = workouts.reduce((a, b) => ((a.total_volume || a.volume || 0)) > ((b.total_volume || b.volume || 0)) ? a : b)
    const bestVol = best.total_volume || best.volume || 0
    if (bestVol) {
      h.push({ type: 'best', text: '最佳训练 ' + best.date + ' — ' + bestVol + 'kg (' + best.sets + '组)' })
    }

    const last = workouts[0]
    if (last) {
      const lastVol = last.total_volume || last.volume || 0
      h.push({ type: 'last', text: '最近训练 ' + last.date + ' · ' + (last.type || '') + ' · ' + lastVol + 'kg' })
    }

    if (weekly.length >= 2) {
      const cur = weekly[weekly.length - 1]
      const prev = weekly[weekly.length - 2]
      if (cur && prev && prev.volume > 0) {
        const diff = ((cur.volume - prev.volume) / prev.volume * 100).toFixed(0)
        const sign = diff > 0 ? '↑' : '↓'
        h.push({ type: 'trend', text: '本周训练量 ' + cur.volume + 'kg (' + cur.sessions + '次) — 较上周' + sign + Math.abs(diff) + '%' })
      }
    }
    return h
  },

  onTab(e) {
    const filter = e.currentTarget.dataset.tab
    const filtered = filter === 'All'
      ? this.data.recent
      : this.data.recent.filter(r => r.type === filter)
    this.setData({ tabFilter: filter, filteredRecent: filtered })
  }
})
