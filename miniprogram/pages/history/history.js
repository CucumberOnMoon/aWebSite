const api = require('../../utils/api')

const TYPE_LABEL = { push: '推', pull: '拉', legs: '腿', Push: '推', Pull: '拉', Legs: '腿' }

Page({
  data: {
    list: [],
    loading: true
  },

  onShow() {
    const app = getApp()
    if (!app.globalData.username) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const raw = await api.getWorkouts(30)
      const list = (raw || []).map(w => ({
        id: w.id,
        date: w.date || '',
        type: (w.type || '').toLowerCase(),
        typeLabel: TYPE_LABEL[w.type] || w.type || '',
        duration: w.duration_min ? w.duration_min + '分钟' : '-',
        sets: w.sets || 0,
        volume: w.total_volume || 0
      }))
      this.setData({ list, loading: false })
    } catch (_) {
      this.setData({ loading: false })
    }
  }
})
