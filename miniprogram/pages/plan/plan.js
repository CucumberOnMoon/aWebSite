const api = require('../../utils/api')

const DOW_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const TYPES = [
  { key: 'Push', label: '推' },
  { key: 'Pull', label: '拉' },
  { key: 'Legs', label: '腿' },
  { key: 'Rest', label: '休息' },
]

Page({
  data: {
    dowNames: DOW_NAMES,
    dow: 1,
    type: 'Push',
    types: TYPES,
    items: [],
    exercises: [],
    showPicker: false,
    pickerList: [],
    pickerCategory: 'Push',
    categories: ['Push', 'Pull', 'Legs'],
    saving: false,
  },

  async onLoad() {
    const today = new Date().getDay()
    this.setData({ dow: today })
    await this.loadAll()
    this.loadDay(today)
  },

  noop() {},

  async loadAll() {
    try {
      const [plan, ex] = await Promise.all([api.getPlan(), api.getExercises()])
      this._plan = (plan && plan.days) || []
      this.setData({ exercises: ex || [] })
    } catch (e) {
      this._plan = []
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  },

  loadDay(dow) {
    const day = (this._plan || []).find(d => d.dow === dow)
    const items = (day && day.items ? day.items : []).map((it, i) => ({
      seq: i + 1,
      exercise_id: it.exercise_id,
      exercise_name: it.exercise_name,
      target_sets: it.target_sets || 3,
      target_reps: it.target_reps || 10,
      note: it.note || '',
    }))
    this.setData({ dow, type: day ? day.type : 'Push', items })
  },

  onDowTap(e) {
    this.loadDay(Number(e.currentTarget.dataset.dow))
  },

  onTypeTap(e) {
    const type = e.currentTarget.dataset.type
    this.setData({ type })
    if (type === 'Rest') this.setData({ items: [] })
  },

  // ── 动作选择 ─────────────────────────
  openPicker() {
    const cat = this.data.type === 'Rest' ? 'Push' : this.data.type
    this._kw = ''
    this.setData({ showPicker: true, pickerCategory: cat })
    this.filterPicker(cat, '')
  },
  closePicker() {
    this.setData({ showPicker: false })
  },
  onPickerCat(e) {
    const cat = e.currentTarget.dataset.cat
    this.setData({ pickerCategory: cat })
    this.filterPicker(cat, this._kw || '')
  },
  onPickerSearch(e) {
    this._kw = e.detail.value || ''
    this.filterPicker(this.data.pickerCategory, this._kw)
  },
  filterPicker(cat, kw) {
    const k = (kw || '').toLowerCase()
    const list = (this.data.exercises || []).filter(ex =>
      ex.category === cat && (!k || (ex.name || '').toLowerCase().includes(k)))
    this.setData({ pickerList: list })
  },
  onPickExercise(e) {
    const id = Number(e.currentTarget.dataset.id)
    const ex = (this.data.exercises || []).find(x => Number(x.id) === id)
    if (!ex) return
    const items = this.data.items.slice()
    if (items.some(it => Number(it.exercise_id) === id)) {
      wx.showToast({ title: '已经在计划里了', icon: 'none' })
      return
    }
    items.push({
      exercise_id: id, exercise_name: ex.name,
      target_sets: 3, target_reps: 10, note: '',
    })
    items.forEach((it, i) => { it.seq = i + 1 })
    this.setData({ items, showPicker: false })
  },
  onRemoveItem(e) {
    const idx = Number(e.currentTarget.dataset.idx)
    const items = this.data.items.slice()
    items.splice(idx, 1)
    items.forEach((it, i) => { it.seq = i + 1 })
    this.setData({ items })
  },
  onSetsChange(e) {
    const idx = Number(e.currentTarget.dataset.idx)
    const delta = Number(e.currentTarget.dataset.delta)
    const items = this.data.items.slice()
    items[idx].target_sets = Math.max(1, Math.min(20, (items[idx].target_sets || 3) + delta))
    this.setData({ items })
  },
  onRepsChange(e) {
    const idx = Number(e.currentTarget.dataset.idx)
    const delta = Number(e.currentTarget.dataset.delta)
    const items = this.data.items.slice()
    items[idx].target_reps = Math.max(1, Math.min(50, (items[idx].target_reps || 10) + delta))
    this.setData({ items })
  },

  // ── 保存 / 清空 ───────────────────────
  async onSave() {
    if (this.data.saving) return
    this.setData({ saving: true })
    try {
      const payload = this.data.items.map(it => ({
        exercise_id: it.exercise_id,
        target_sets: it.target_sets,
        target_reps: it.target_reps,
        note: it.note || null,
      }))
      await api.savePlan(this.data.dow, this.data.type, payload)
      wx.showToast({ title: '已保存', icon: 'success' })
      await this.loadAll()
      this.loadDay(this.data.dow)
    } catch (e) {
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },

  async onClear() {
    const res = await wx.showModal({ title: '清空这一天', content: '清空后这一天就没有计划了' })
    if (!res.confirm) return
    try {
      await api.deletePlan(this.data.dow)
      await this.loadAll()
      this.loadDay(this.data.dow)
      wx.showToast({ title: '已清空', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: e.message || '清空失败', icon: 'none' })
    }
  },
})
