const api = require('../../utils/api')

Page({
  data: {
    list: [],
    loading: true
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
  }
})
