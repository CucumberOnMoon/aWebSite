const api = require('../../utils/api')

const WEEK_CYCLE = ['push', 'pull', 'legs', 'push', 'pull', 'legs', 'rest']

// 组间休息时间（秒）
function calcRestTime(exName) {
  if (exName.includes('深蹲') || exName.includes('卧推')) return 180
  if (exName.includes('划船') || exName.includes('下拉') || exName.includes('引体')) return 120
  return 90
}

// 重量选项 2.5~150kg 步进2.5
function genWeights() {
  const w = []
  for (let i = 2.5; i <= 150; i += 2.5) {
    w.push(i % 1 === 0 ? i : Math.round(i * 10) / 10)
  }
  return w
}
const WEIGHT_OPTIONS = genWeights()
const WEIGHT_LABELS = WEIGHT_OPTIONS.map(w => w + 'kg')

// 次数选项 1~30
const REPS_OPTIONS = Array.from({ length: 30 }, (_, i) => i + 1)
const REPS_LABELS = REPS_OPTIONS.map(r => r + '次')

Page({
  data: {
    workoutId: null,
    startTime: null,
    timer: '00:00',
    loading: true,
    // 当日动作列表
    exOptions: [],
    exLabels: [],
    // 三个下拉框当前选中索引
    exIdx: 0,
    weightIdx: 0,
    repsIdx: 0,
    // 已记录组（按动作分组）
    loggedGroups: [],
    // 下拉框选项数据
    weightOptions: WEIGHT_OPTIONS,
    weightLabels: WEIGHT_LABELS,
    repsOptions: REPS_OPTIONS,
    repsLabels: REPS_LABELS,
    // 组间休息倒计时
    resting: false,
    restSeconds: 0,
    restTotal: 0
  },

  timerRef: null,
  restTimerRef: null,

  onLoad(options) {
    const wid = parseInt(options.wid)
    this.setData({ workoutId: wid, startTime: Date.now() })
    this.loadExercises()
    this.startTimer()
  },

  onUnload() {
    if (this.timerRef) clearInterval(this.timerRef)
    if (this.restTimerRef) clearInterval(this.restTimerRef)
  },

  startTimer() {
    this.timerRef = setInterval(() => {
      const sec = Math.floor((Date.now() - this.data.startTime) / 1000)
      this.setData({
        timer: String(Math.floor(sec / 60)).padStart(2, '0') + ':' + String(sec % 60).padStart(2, '0')
      })
    }, 1000)
  },

  async loadExercises() {
    try {
      const allExs = await api.getExercises()
      const dow = new Date().getDay()
      const idx = dow === 0 ? 6 : dow - 1
      const todayType = WEEK_CYCLE[idx] || 'rest'
      const dayExs = (allExs || []).filter(e => (e.category || '').toLowerCase() === todayType)

      const exOptions = dayExs.map(e => ({ id: e.id, name: e.name }))
      const exLabels = exOptions.map(e => e.name)

      this.setData({
        exOptions,
        exLabels,
        loading: false
      })
      this.loadLoggedSets()
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'error' })
      this.setData({ loading: false })
    }
  },

  async loadLoggedSets() {
    try {
      const allSets = await api.getWorkoutSets(this.data.workoutId)
      const groups = []
      const exMap = {}
      for (const s of allSets || []) {
        const ename = s.exercise || s.name || ''
        if (!exMap[ename]) {
          exMap[ename] = { name: ename, sets: [] }
          groups.push(exMap[ename])
        }
        exMap[ename].sets.push({
          num: s.set_number || (exMap[ename].sets.length + 1),
          weight_kg: s.weight_kg,
          reps: s.reps
        })
      }
      this.setData({ loggedGroups: groups })
    } catch (_) {}
  },

  // 三个下拉框切换
  onExChange(e) {
    this.setData({ exIdx: e.detail.value })
  },
  onWeightChange(e) {
    this.setData({ weightIdx: e.detail.value })
  },
  onRepsChange(e) {
    this.setData({ repsIdx: e.detail.value })
  },

  // 添加一组 → 保存 → 开始组间倒计时
  async onAddSet() {
    const { exOptions, exIdx, weightOptions, weightIdx, repsOptions, repsIdx, workoutId, loggedGroups } = this.data
    const ex = exOptions[exIdx]
    if (!ex) { wx.showToast({ title: '请选择动作', icon: 'none' }); return }

    const weight = weightOptions[weightIdx]
    const reps = repsOptions[repsIdx]

    wx.showLoading({ title: '保存...' })

    try {
      const group = loggedGroups.find(g => g.name === ex.name)
      const setNum = group ? group.sets.length + 1 : 1

      await api.logSet(workoutId, ex.id, weight, reps, 0, setNum)

      // 更新本地已记录
      const newSet = { num: setNum, weight_kg: weight, reps }
      if (group) {
        group.sets.push(newSet)
      } else {
        loggedGroups.push({ name: ex.name, sets: [newSet] })
      }
      this.setData({ loggedGroups: [...loggedGroups] })

      wx.hideLoading()
      wx.showToast({ title: '✓ 第' + setNum + '组 ' + ex.name, icon: 'success', duration: 600 })

      // 开始组间倒计时
      this.startRestCountdown(ex.name)
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '保存失败', icon: 'error' })
    }
  },

  startRestCountdown(exName) {
    // 清除上一个倒计时
    if (this.restTimerRef) clearInterval(this.restTimerRef)

    const total = calcRestTime(exName)
    this.setData({ resting: true, restSeconds: total, restTotal: total })

    this.restTimerRef = setInterval(() => {
      let sec = this.data.restSeconds - 1
      if (sec <= 0) {
        clearInterval(this.restTimerRef)
        this.restTimerRef = null
        this.setData({ resting: false, restSeconds: 0 })
        wx.showToast({ title: '休息结束 💪', icon: 'none', duration: 1000 })
      } else {
        this.setData({ restSeconds: sec })
      }
    }, 1000)
  },

  onFinish() {
    wx.showModal({
      title: '完成训练',
      content: '确定结束本次训练吗？',
      success: async (res) => {
        if (!res.confirm) return
        if (this.timerRef) clearInterval(this.timerRef)
        if (this.restTimerRef) clearInterval(this.restTimerRef)
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
