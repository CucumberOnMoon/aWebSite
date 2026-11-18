const api = require('../../utils/api')

// 围度字段定义（顺序即展示顺序）
const FIELDS = [
  { key: 'chest_cm', label: '胸围', hint: '选填' },
  { key: 'waist_cm', label: '腰围', hint: '自然呼气末' },
  { key: 'hip_cm', label: '臀围', hint: '选填' },
  { key: 'thigh_cm', label: '大腿', hint: '站直放松，最高处' },
  { key: 'calf_cm', label: '小腿', hint: '最粗处' },
  { key: 'arm_cm', label: '二头', hint: '屈臂用力' },
]

Page({
  data: {
    loading: true,
    failed: false,
    hasData: false,
    userList: [],
    selectedUser: '',
    showUserList: false,
    fields: FIELDS,
    latest: null,
    history: [],
  },

  onShow() {
    this.loadUsers()
    this.init()
  },

  async loadUsers() {
    try { this.setData({ userList: await api.getUsers() || [] }) } catch (_) {}
  },

  async init() {
    this.setData({ loading: true, failed: false })
    try {
      const { code } = await wx.login()
      const res = await api.wechatLogin(code)
      if (res && res.bound && res.username) {
        api.setCurrentUser(res.username)
        this.setData({ selectedUser: res.username })
        this.load()
      } else {
        this.setData({ loading: false, failed: true })
      }
    } catch (_) {
      this.setData({ loading: false, failed: true })
    }
  },

  async load() {
    this.setData({ loading: true, failed: false })
    try {
      const r = await api.getMeasurements()
      const latest = this.format(r.latest)
      const history = (r.results || []).map(x => this.format(x)).reverse()
      this.setData({
        loading: false,
        hasData: !!(latest || history.length),
        latest,
        history,
      })
    } catch (e) {
      console.error('围度加载失败', e)
      this.setData({ loading: false, failed: true })
    }
  },

  // 数值统一 1 位小数（后端给 float，直接显示会变整数）
  format(m) {
    if (!m) return null
    const out = Object.assign({}, m)
    FIELDS.forEach(f => {
      out[f.key] = (m[f.key] === null || m[f.key] === undefined) ? null : Number(m[f.key]).toFixed(1)
    })
    ;['thigh_calf_diff', 'thigh_waist_diff'].forEach(k => {
      out[k] = (m[k] === null || m[k] === undefined) ? null : Number(m[k]).toFixed(1)
    })
    ;['waist_height_ratio', 'arm_thigh_ratio'].forEach(k => {
      out[k] = (m[k] === null || m[k] === undefined) ? null : Number(m[k]).toFixed(3)
    })
    return out
  },

  // ── 用户下拉（与段位页一致）──────────────────
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
  },

});
