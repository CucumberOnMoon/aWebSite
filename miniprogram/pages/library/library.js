const api = require('../../utils/api')
const { EXERCISE_INFO, CATEGORY_MUSCLE_MAP, MUSCLE_LABELS, CATEGORY_LABELS } = require('../../utils/exercises')

const CATEGORIES = ['Push', 'Pull', 'Legs', 'Core', 'Other']

Page({
  data: {
    loading: false,
    allExercises: [],
    categoryTab: 'Push',
    muscleFilter: '',
    muscleOptions: [],
    filteredList: [],
    showExDetail: false,
    exDetailData: null,
    MUSCLE_LABELS, CATEGORY_LABELS,
    CAT_KEYS: ['Push', 'Pull', 'Legs', 'Core', 'Other'],
    muscleIdx: 0,
    currentMuscleLabel: '全部',
  },

  async onShow() {
    this.setData({ loading: true })
    try {
      const list = await api.getExercises()
      if (list && list.length) {
        this.setData({ allExercises: list })
        this.applyFilter()
      }
    } catch (_) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
    this.setData({ loading: false })
  },

  // ── 分类标签切换 ──
  onCategoryTap(e) {
    const tab = e.currentTarget.dataset.cat
    this.setData({ categoryTab: tab, muscleFilter: '' })
    this.applyFilter()
  },

  // ── 肌群下拉切换 ──
  onMuscleChange(e) {
    const idx = parseInt(e.detail.value) || 0
    const options = this.data.muscleOptions
    const val = (options[idx] && options[idx].value) || ''
    this.setData({ muscleFilter: val })
    this.applyFilter()
  },

  applyFilter() {
    const { allExercises, categoryTab, muscleFilter } = this.data
    let filtered = allExercises.filter(e => e.category === categoryTab)
    if (muscleFilter) {
      filtered = filtered.filter(e => e.target_muscle === muscleFilter)
    }
    filtered.sort((a, b) => {
      const ta = a.target_muscle || ''
      const tb = b.target_muscle || ''
      if (ta !== tb) return ta.localeCompare(tb)
      return a.id - b.id
    })
    const muscles = CATEGORY_MUSCLE_MAP[categoryTab] || []
    const catCount = allExercises.filter(e => e.category === categoryTab).length
    const muscleOptions = [{ value: '', label: `全部 (${catCount})` }]
      .concat(muscles.map(m => ({
        value: m,
        label: (MUSCLE_LABELS[m] || m) + ` (${allExercises.filter(e => e.category === categoryTab && e.target_muscle === m).length})`
      })))
    const muscleIdx = muscleFilter
      ? Math.max(0, muscleOptions.findIndex(o => o.value === muscleFilter))
      : 0
    const currentMuscleLabel = muscleOptions[muscleIdx]?.label || '全部'
    this.setData({ filteredList: filtered, muscleOptions, muscleIdx, currentMuscleLabel })
  },

  // ── 动作详情弹窗 ──
  onExTap(e) {
    const name = e.currentTarget.dataset.exname
    const ex = this.data.allExercises.find(e => e.name === name) || {}
    const info = EXERCISE_INFO[name] || {}
    const imgName = info.muscles ? name : (ex.target_muscle && ex.target_muscle !== 'NULL' ? ex.target_muscle : null)
    this.setData({ showExDetail: true, exDetailData: { name, imgName, name_cn: ex.name_cn || ex.name, target_muscle: ex.target_muscle || '', ...info } })
    // 异步加载 GIF
    api.getExerciseGif(name).then(res => {
      if (res && res.gif_url) {
        this.setData({ 'exDetailData.gif_url': res.gif_url })
      }
    }).catch(() => {})
  },

  dismissExDetail() {
    this.setData({ showExDetail: false, exDetailData: null })
  },

  noop() {},
})
