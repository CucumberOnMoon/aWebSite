const api = require('../../utils/api')

// 围度字段定义（顺序即展示顺序）
const FIELDS = [
  { key: 'shoulder_cm', label: '肩围', hint: '两肩峰最外点' },
  { key: 'chest_cm', label: '胸围', hint: '乳头水平一圈' },
  { key: 'waist_cm', label: '腰围', hint: '自然呼气末' },
  { key: 'hip_cm', label: '臀围', hint: '臀部最凸处' },
  { key: 'thigh_cm', label: '大腿', hint: '站直放松，最高处' },
  { key: 'calf_cm', label: '小腿', hint: '最粗处' },
  { key: 'arm_cm', label: '二头', hint: '屈臂用力' },
]

// 派生比值（服务端算好，这里只排版）
const RATIOS = [
  { key: 'shoulder_chest_ratio', label: '肩 / 胸', ref: '1.05–1.15 正常' },
  { key: 'shoulder_waist_ratio', label: '肩 / 腰', ref: '＞1.30 倒三角' },
  { key: 'waist_hip_ratio', label: '腰 / 臀', ref: '＜0.90 健康' },
  { key: 'waist_height_ratio', label: '腰 / 身高', ref: '＜0.50 健康' },
  { key: 'thigh_waist_diff', label: '大腿 − 腰', ref: '＞15 下肢占优' },
  { key: 'thigh_calf_diff', label: '大腿 − 小腿', ref: '18–22 正常' },
  { key: 'arm_thigh_ratio', label: '臂 / 腿', ref: '0.58–0.62 正常' },
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
    ratios: RATIOS,
    latest: null,
    radar: [],
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
        radar: (r.latest && r.latest.radar) || [],
        history,
      }, () => this.drawRatios())
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
    ;['waist_height_ratio', 'arm_thigh_ratio', 'shoulder_chest_ratio',
      'shoulder_waist_ratio', 'waist_hip_ratio'].forEach(k => {
      out[k] = (m[k] === null || m[k] === undefined) ? null : Number(m[k]).toFixed(3)
    })
    return out
  },

  // ── 7 项身体比例雷达（值 = 后端给的 0-1 达标度）────
  drawRatios() {
    const data = this.data.radar || []
    if (!data.length) return
    wx.createSelectorQuery().in(this).select('#ratioRadar')
      .fields({ node: true, size: true })
      .exec((res) => {
        const r = res && res[0]
        if (!r || !r.node) return
        const canvas = r.node
        const ctx = canvas.getContext('2d')
        const dpr = (wx.getWindowInfo ? wx.getWindowInfo().pixelRatio : 2) || 2
        const W = r.width, H = r.height
        canvas.width = W * dpr
        canvas.height = H * dpr
        ctx.scale(dpr, dpr)
        ctx.clearRect(0, 0, W, H)

        const cx = W / 2, cy = H / 2
        const R = Math.min(W, H) / 2 - 34
        const n = data.length
        const ang = i => -Math.PI / 2 + i * 2 * Math.PI / n
        const pt = (i, ratio) => [
          cx + Math.cos(ang(i)) * R * ratio,
          cy + Math.sin(ang(i)) * R * ratio,
        ]

        // 网格
        ctx.strokeStyle = '#30363d'
        ctx.lineWidth = 1
        for (let ring = 1; ring <= 4; ring++) {
          ctx.beginPath()
          for (let i = 0; i < n; i++) {
            const [x, y] = pt(i, ring / 4)
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
          }
          ctx.closePath()
          ctx.stroke()
        }
        for (let i = 0; i < n; i++) {
          const [x, y] = pt(i, 1)
          ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y); ctx.stroke()
        }

        // 数据多边形（null 视为 0）
        ctx.beginPath()
        data.forEach((d, i) => {
          const v = Math.max(0.04, Number(d.score) || 0)
          const [x, y] = pt(i, v)
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        })
        ctx.closePath()
        ctx.fillStyle = 'rgba(63,185,80,0.20)'
        ctx.fill()
        ctx.strokeStyle = '#3fb950'
        ctx.lineWidth = 2
        ctx.stroke()

        // 点 + 标签
        ctx.font = '9px sans-serif'
        data.forEach((d, i) => {
          const v = Math.max(0.04, Number(d.score) || 0)
          const [x, y] = pt(i, v)
          ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2)
          ctx.fillStyle = d.score === null ? '#6e7681' : '#3fb950'
          ctx.fill()

          const [lx, ly] = pt(i, 1.2)
          ctx.fillStyle = d.score === null ? '#484f58' : '#8b949e'
          ctx.textAlign = Math.abs(lx - cx) < 4 ? 'center' : (lx > cx ? 'left' : 'right')
          ctx.textBaseline = 'middle'
          ctx.fillText(d.label, lx, ly)
        })
      })
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
