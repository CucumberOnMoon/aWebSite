const api = require('./utils/api')

App({
  globalData: {
    username: '',
    password: '',
  },

  onLaunch() {
    // 尝试自动登录（从缓存恢复）
    const info = wx.getStorageSync('userInfo')
    if (info && info.username && info.password) {
      api.setAuth(info.username, info.password)
      this.globalData.username = info.username
      this.globalData.password = info.password
    }
  }
})
