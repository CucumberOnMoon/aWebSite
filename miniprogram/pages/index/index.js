Page({
  data: {
    greeting: 'Hello World',
    timestamp: ''
  },
  onLoad() {
    this.setData({
      timestamp: new Date().toLocaleString()
    })
  }
})
