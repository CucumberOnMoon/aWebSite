const api = require('./utils/api')

App({
  globalData: {
    selectedUser: ''
  },

  onLaunch() {
    const saved = wx.getStorageSync('selectedUser')
    if (saved) {
      api.setCurrentUser(saved)
      this.globalData.selectedUser = saved
    }
  }
})
