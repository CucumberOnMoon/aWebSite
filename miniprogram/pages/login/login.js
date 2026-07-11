const api = require('../../utils/api')

Page({
  data: {
    username: '',
    password: '',
    loading: false,
    error: ''
  },

  onLoad() {
    const app = getApp()
    if (app.globalData.username) {
      this.checkAuth()
    }
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  async onLogin() {
    const { username, password } = this.data
    if (!username || !password) {
      this.setData({ error: '请输入用户名和密码' })
      return
    }

    this.setData({ loading: true, error: '' })
    api.setAuth(username, password)

    try {
      await api.checkAuth()
      // 登录成功，存缓存
      wx.setStorageSync('userInfo', { username, password })
      const app = getApp()
      app.globalData.username = username
      app.globalData.password = password
      wx.reLaunch({ url: '/pages/home/home' })
    } catch (e) {
      api.clearAuth()
      this.setData({
        error: e.message === 'UNAUTHORIZED' ? '用户名或密码错误' : e.message,
        loading: false
      })
    }
  },

  async checkAuth() {
    try {
      await api.checkAuth()
      wx.reLaunch({ url: '/pages/home/home' })
    } catch (e) {
      // 存的身份过期了，清除让用户重新登录
      api.clearAuth()
      const app = getApp()
      app.globalData.username = ''
      app.globalData.password = ''
      wx.removeStorageSync('userInfo')
      console.warn('自动登录失败，请重新登录:', e.message)
    }
  },
})
