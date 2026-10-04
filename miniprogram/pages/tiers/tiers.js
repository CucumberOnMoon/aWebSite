const api = require('../../utils/api')

// 8 档段位配色 + emoji（按 tier 名映射，与后端命名一一对应）
const TIER_STYLE = {
  '倔强青铜': { color: '#8b6b4a', emoji: '🥉' },
  '秩序白银': { color: '#a8b3b8', emoji: '🥈' },
  '荣耀黄金': { color: '#f5c342', emoji: '🥇' },
  '尊贵铂金': { color: '#7fd8e8', emoji: '💠' },
  '永恒钻石': { color: '#a78bfa', emoji: '💎' },
  '至尊星耀': { color: '#f778ba', emoji: '⭐' },
  '最强王者': { color: '#ff7b72', emoji: '👑' },
  '荣耀王者': { color: '#ffb020', emoji: '🏆' },
}
// 兜底：未知段位名时按 tier_index 取色
const FALLBACK_COLORS = ['#8b6b4a', '#a8b3b8', '#f5c342', '#7fd8e8', '#a78bfa', '#f778ba', '#ff7b72', '#ffb020']


Page({
  data: {
    loading: true,
    userList: [],
    selectedUser: '',
    tiers: [],
    updatedAt: '',
    bodyweight: null,
    hasData: false,
    failed: false,
    tierPopup: null,
    listPopup: false,
    // 段位表弹窗数据（全部来自 /api/fitness/tiers/legend/）
    legend: null,
    legendRows: [],
    legendLoading: false,
    legendFailed: false,
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
        // 未绑定：回首页处理绑定
        this.setData({ loading: false, failed: true })
      }
    } catch (_) {
      this.setData({ loading: false, failed: true })
    }
  },

  onUserChange(e) {
    const user = this.data.userList[e.detail.value]
    if (user) {
      api.setCurrentUser(user)
      // 换用户 → 体重可能不同，legend 缓存作废
      this.setData({ selectedUser: user, legend: null, legendRows: [] })
      this.load()
    }
  },

  // ── 段位说明弹窗（单个段位，数据取自 legend）──────────
  onTierTap(e) {
    const tier = e.currentTarget.dataset.tier
    if (!tier) return
    const t = this.findLegendTier(tier)
    if (!t) {
      // legend 还没加载或没有该档：至少显示名字
      const color = (TIER_STYLE[tier] || {}).color || '#8b949e'
      this.setData({ tierPopup: { title: tier, nums: '', body: '暂无说明', mark: '', color } })
      return
    }
    this.setData({
      tierPopup: {
        title: t.emoji + ' ' + t.name,
        nums: '',
        body: t.profile || '',
        mark: t.marker || '',
        color: t.color,
      },
    })
  },
  dismissTierPopup() {
    this.setData({ tierPopup: null })
  },

  findLegendTier(name) {
    const legend = this.data.legend
    if (!legend || !Array.isArray(legend.tiers)) return null
    return legend.tiers.find(t => t.name === name) || null
  },

  // ── 段位列表弹窗（打开时才请求 legend）──────────────────
  async onShowTierList() {
    this.setData({ listPopup: true })
    if (this.data.legend) return          // 已加载过，不重复请求
    this.loadLegend()
  },

  async loadLegend() {
    this.setData({ legendFailed: false, legendLoading: true })
    try {
      const res = await api.getTiersLegend()
      if (!res || !res.count || !Array.isArray(res.tiers)) {
        this.setData({ legendLoading: false, legendFailed: true })
        return
      }
      this.setData({
        legend: res,
        legendRows: this.buildLegendRows(res),
        legendLoading: false,
        legendFailed: false,
      })
    } catch (err) {
      console.error('段位表加载失败:', err)
      this.setData({ legendLoading: false, legendFailed: true })
    }
  },

  // 把 legend 转成弹窗渲染用的结构：按「段位」分组，每档列出各动作要求
  buildLegendRows(res) {
    const tiers = res.tiers || []
    const lifts = res.lifts || []
    const order = res.legend_order || []
    const byName = {}
    for (const l of lifts) byName[l.lift] = l
    // 按 legend_order 取动作（顺序不重排）
    const picked = order.map(n => byName[n]).filter(Boolean)

    return tiers.map((t, i) => {
      const items = picked.map(l => {
        let need = ''
        if (l.metric === 'reps') {
          const v = l.thresholds && l.thresholds[i]
          need = v != null ? v + ' ' + (l.unit || '个') : '—'
        } else {
          const w = l.working_kg_10 && l.working_kg_10[i]
          if (w == null) {
            const nxt = l.working_kg_10 && l.working_kg_10[1]
            need = nxt != null ? '＜' + nxt + 'kg × 10' : '—'
          } else {
            need = w + 'kg × 10'
          }
        }
        return { lift: l.lift, need }
      })
      return {
        name: t.name,
        index: t.index,
        color: t.color,
        emoji: t.emoji,
        profile: t.profile || '',
        marker: t.marker || '',
        items,
      }
    })
  },

  retryLegend() {
    this.loadLegend()
  },
  dismissTierList() {
    this.setData({ listPopup: false })
  },
  noop() {},

  async load() {
    this.setData({ loading: true, failed: false })
    try {
      const res = await api.getTiers()
      if (!res || !res.count || !Array.isArray(res.results)) {
        this.setData({ loading: false, tiers: [], hasData: false })
        return
      }
      const tiers = res.results.map(r => this.formatRow(r))
      this.setData({
        loading: false,
        hasData: true,
        tiers,
        updatedAt: res.updated_at || '',
        bodyweight: res.bodyweight != null ? res.bodyweight : null,
      })
    } catch (err) {
      console.error('段位加载失败:', err)
      this.setData({ loading: false, failed: true, tiers: [], hasData: false })
    }
  },

  formatRow(r) {
    const isRatio = r.metric === 'ratio'
    const idx = typeof r.tier_index === 'number' ? r.tier_index : 0
    const style = TIER_STYLE[r.tier] || { color: FALLBACK_COLORS[Math.min(idx, 7)], emoji: '' }
    const color = style.color
    const pct = typeof r.progress_pct === 'number' ? r.progress_pct : 0

    // 先算好，避免下面引用时踩字段名
    const nextTier = r.next_tier || ''
    const nextTarget = r.next_target || ''
    // reps 类 next_e1rm_kg 为 null
    const nextE1rm = r.next_e1rm_kg
    const nextNeed = r.next_need
    const curValue = r.cur_value
    // → 尊贵铂金（67.5kg × 10 ｜ e1RM 90）  /  → 荣耀黄金（6 个）
    let nextText = ''
    if (nextTier) {
      let inner = ''
      if (nextTarget && nextE1rm != null) {
        inner = nextTarget + ' ｜ e1RM ' + nextE1rm
      } else if (nextTarget) {
        inner = nextTarget
      } else if (nextNeed != null) {
        inner = isRatio ? String(nextNeed) : Math.round(nextNeed) + ' 个'
      }
      nextText = inner ? '→ ' + nextTier + '（' + inner + '）' : '→ ' + nextTier
    }

    // 本次变化角标：delta 为 null → 升段（进度重置），显示 🏆 不显示百分比
    const delta = r.progress_delta
    let deltaText = ''
    let deltaClass = ''
    let tierUp = false
    if (delta === null || delta === undefined) {
      if (r.progress_delta === null) {
        // 显式 null = 本次升段
        tierUp = true
        deltaText = '🏆 升段'
        deltaClass = 'dl-up'
      }
      // undefined（字段缺失）时什么都不显示
    } else if (typeof delta === 'number' && Math.abs(delta) >= 1) {
      if (delta > 0) {
        deltaText = '↑+' + Math.round(delta) + '%'
        deltaClass = 'dl-up'
      } else {
        deltaText = '↓' + Math.round(delta) + '%'
        deltaClass = 'dl-down'
      }
    }

    return {
      lift: r.lift,
      tier: r.tier || '—',
      tierEmoji: style.emoji,
      color,
      progressPct: pct,
      // 优先显示后端给的当前做组文案（cur_target）；reps 型或缺失时退回倍数/个数
      curText: r.cur_target
        ? r.cur_target
        : (isRatio
            ? (curValue != null ? Number(curValue).toFixed(2) + '×' : '—')
            : (curValue != null ? Math.round(curValue) + ' 个' : '—')),
      e1rmText: r.e1rm_kg != null ? 'e1RM ' + r.e1rm_kg + 'kg' : '',
      nextText,
      deltaText,
      deltaClass,
      tierUp,
      bestDate: r.best_date || '',
      isMax: !nextTier,
    }
  },
})
