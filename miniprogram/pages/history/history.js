const api = require('../../utils/api')

Page({
  data: {
    list: [],
    loading: true,
    calPopup: null, calPopupData: null,
  },

  onShow() {
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const raw = await api.getWorkouts(30)
      const list = (raw || []).map(w => ({
        id: w.id, date: w.date || '',
        type: (w.type || '').toLowerCase(),
        typeLabel: ((w.type || '')[0] || ''),
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
