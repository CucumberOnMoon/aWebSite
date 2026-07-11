const api = require('../../utils/api')

const WEEK_CYCLE = ['push', 'pull', 'legs', 'push', 'pull', 'legs', 'rest']

Page({
  data: {
    workoutId: null,
    startTime: null,
    timer: '00:00',
    exList: [],
    loading: true
  },

  timerRef: null,

  onLoad(options) {
    const wid = parseInt(options.wid)
    this.setData({ workoutId: wid, startTime: Date.now() })
    this.loadExercises()
    this.startTimer()
  },

  onUnload() {
    if (this.timerRef) clearInterval(this.timerRef)
  },

  startTimer() {
    this.timerRef = setInterval(() => {
      const sec = Math.floor((Date.now() - this.data.startTime) / 1000)
      const m = String(Math.floor(sec / 60)).padStart(2, '0')
      const s = String(sec % 60).padStart(2, '0')
      this.setData({ timer: m + ':' + s })
    }, 1000)
  },

  async loadExercises() {
    try {
      const allExs = await api.getExercises()
      const dow = new Date().getDay()
      const idx = dow === 0 ? 6 : dow - 1
      const todayType = WEEK_CYCLE[idx] || 'rest'

      const dayExs = (allExs || [])
        .filter(e => (e.category || '').toLowerCase() === todayType)

      const exList = dayExs.map(e => ({
        id: e.id,
        name: e.name,
        sets: [],
        open: false,
        inWeight: '',
        inReps: '',
        inRir: '0',
        done: false
      }))

      if (exList.length) exList[0].open = true

      this.setData({ exList, loading: false })
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  onToggle(e) {
    const idx = e.currentTarget.dataset.idx
    const key = 'exList[' + idx + '].open'
    this.setData({ [key]: !this.data.exList[idx].open })
  },

  onIn(e) {
    const idx = e.currentTarget.dataset.idx
    const field = e.currentTarget.dataset.field
    this.setData({ ['exList[' + idx + '].' + field]: e.detail.value })
  },

  async onAddSet(e) {
    const idx = e.currentTarget.dataset.idx
    const ex = this.data.exList[idx]
    const weight = parseFloat(ex.inWeight)
    const reps = parseInt(ex.inReps)
    const rir = parseInt(ex.inRir) || 0

    if (!weight || !reps) {
      wx.showToast({ title: '请输入重量和次数', icon: 'none' })
      return
    }

    wx.showLoading({ title: '保存...' })
    try {
      const res = await api.logSet(this.data.workoutId, ex.id, weight, reps, rir)
      const num = ex.sets.length + 1
      const newSet = { sid: res.id || num, num, weight_kg: weight, reps, rir }

      const key = 'exList[' + idx + '].sets'
      this.setData({
        [key]: [...ex.sets, newSet],
        ['exList[' + idx + '].inWeight']: '',
        ['exList[' + idx + '].inReps']: '',
        ['exList[' + idx + '].inRir']: '0'
      })

      wx.hideLoading()
      wx.showToast({ title: '✓ 第' + num + '组', icon: 'success', duration: 800 })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '保存失败', icon: 'error' })
    }
  },

  onFinish() {
    wx.showModal({
      title: '完成训练',
      content: '确定结束本次训练吗？',
      success: async (res) => {
        if (!res.confirm) return
        if (this.timerRef) clearInterval(this.timerRef)
        const min = Math.floor((Date.now() - this.data.startTime) / 60000)

        try {
          await api.finishWorkout(this.data.workoutId, min)
          wx.showToast({ title: '训练完成 💪', icon: 'success', duration: 2000 })
          setTimeout(() => wx.navigateBack(), 2000)
        } catch (e) {
          wx.showToast({ title: '保存失败', icon: 'error' })
        }
      }
    })
  }
})
