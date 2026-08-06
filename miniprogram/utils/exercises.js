// ── 动作知识库 ──
const EXERCISE_INFO = {
  '杠铃卧推': {
    muscles: '胸大肌（整体）· 三角肌前束 · 肱三头肌',
    notes: '肩胛骨全程收紧贴凳 · 杠铃触胸即起 · 手腕中立不后翻 · 脚踩实地面'
  },
  '杠铃上斜卧推': {
    muscles: '胸大肌（上胸）· 三角肌前束 · 肱三头肌',
    notes: '凳角30-45° · 杠铃落至上胸 · 肘不过度外展 · 手腕中立不后翻'
  },
  '哑铃上斜卧推': {
    muscles: '胸大肌（上胸）· 三角肌前束 · 肱三头肌',
    notes: '凳角30-45° · 哑铃下落至大小臂90° · 顶点挤压胸 · 肘不过度外展'
  },
  '侧平举': {
    muscles: '三角肌（中束为主）· 冈上肌',
    notes: '身体微前倾稳住肩胛 · 肘微屈固定角度 · 手不高于肘 · 不要借力甩'
  },
  '绳索下压': {
    muscles: '肱三头肌（外侧头+长头）',
    notes: '大臂贴肋不动 · 下压至手臂伸直 · 缓慢回放控制 · 身体勿前后晃'
  },
  '双杠臂屈伸(助力)': {
    muscles: '胸大肌（下胸）· 肱三头肌 · 三角肌前束',
    notes: '含胸微前倾练胸 · 直身上下练三头 · 下落勿过低伤肩 · 肘不内夹'
  },
  '俯卧撑': {
    muscles: '胸大肌 · 三角肌前束 · 肱三头肌 · 核心',
    notes: '身体成直线不塌腰 · 手略宽于肩 · 下落至胸触地 · 肘45°夹'
  },
  '高位下拉': {
    muscles: '背阔肌（宽度）· 肱二头肌 · 大圆肌',
    notes: '肩胛下沉启动 · 拉至锁骨位 · 肘垂直向下画弧 · 躯干微后倾不动晃'
  },
  '低位划船': {
    muscles: '背阔肌（厚度）· 菱形肌 · 斜方肌中束 · 肱二头肌',
    notes: '肩胛后缩启动 · 拉至腹部 · 肘贴肋向后 · 顶峰夹背1秒'
  },
  '面拉': {
    muscles: '三角肌后束 · 冈下肌 · 小圆肌 · 菱形肌',
    notes: '拉至眼前方 · 肘高过腕 · 末端外旋肩 · 轻重量高次数'
  },
  '哑铃弯举': {
    muscles: '肱二头肌（长头+短头）· 肱肌',
    notes: '大臂贴肋不动 · 腕中立 · 全幅度伸到底 · 勿甩腰借力'
  },
  '直臂下压': {
    muscles: '背阔肌（下背）· 大圆肌 · 胸大肌下束（辅助）',
    notes: '肘微屈固定角度 · 身体微前倾 · 下压至大腿侧 · 放回可控'
  },
  '反向蝴蝶机': {
    muscles: '三角肌后束 · 冈下肌 · 小圆肌 · 菱形肌',
    notes: '肩胛打开前伸 · 后拉至与肩平 · 肘微屈 · 勿用背夹代偿'
  },
  '杠铃深蹲': {
    muscles: '股四头肌 · 臀大肌 · 腘绳肌 · 竖脊肌 · 核心',
    notes: '杠铃高杠位 · 膝随脚尖方向 · 核心绷紧不松 · 大腿与地面平行或更低 · 踝活动度不够可垫片'
  },
  '腿屈伸': {
    muscles: '股四头肌（整体，重点股内侧肌）',
    notes: '坐垫调整使膝对准转轴 · 全幅度慢放 · 顶峰挤压 · 勿甩腿借力'
  },
  '保加利亚分腿蹲': {
    muscles: '股四头肌 · 臀大肌 · 腘绳肌 · 核心',
    notes: '后脚垫高 · 躯干微前倾 · 前膝不超脚尖 · 后膝接近地面 · 单边完成再换'
  },
  '腿弯举': {
    muscles: '腘绳肌（股二头肌）· 腓肠肌',
    notes: '髋贴紧凳面 · 全幅度慢放 · 顶峰挤压 · 勿用爆发力甩'
  },
  '提踵': {
    muscles: '腓肠肌 · 比目鱼肌',
    notes: '站姿练腓肠肌 · 坐姿练比目鱼肌 · 全幅度 · 顶峰挤压2秒 · 高次数'
  },
  '相扑深蹲': {
    muscles: '大腿内收肌 · 臀大肌 · 股四头肌',
    notes: '站距宽于肩 · 脚尖外展45° · 膝随脚尖方向 · 上身直立 · 蹲到底'
  },
  '负重臀推': {
    muscles: '臀大肌（主打）· 腘绳肌 · 核心',
    notes: '肩胛骨靠凳 · 髋顶至肩-膝成直线 · 顶峰挤压 · 下放不碰地'
  },
  '助力引体向上': {
    muscles: '背阔肌 · 肱二头肌 · 大圆肌 · 斜方肌',
    notes: '宽握练宽度 · 反握练二头 · 下放到底 · 肩胛主动收紧'
  },
  '罗马尼亚硬拉': {
    muscles: '腘绳肌 · 臀大肌 · 竖脊肌 · 核心',
    notes: '髋向后推启动 · 膝微屈固定 · 杠铃贴腿下放至小腿中 · 腘绳感为主 · 勿弓腰'
  },
  '硬拉': {
    muscles: '全身后侧链：腘绳肌 · 臀大肌 · 竖脊肌 · 背阔肌 · 前臂',
    notes: '杠铃贴胫骨 · 背收紧挺胸 · 髋和肩同步起 · 勿弓腰 · 全程核心绷紧'
  },
}

// ── 肌群映射（分类→肌群列表） ──
const CATEGORY_MUSCLE_MAP = {
  Push: ['pectorals', 'delts', 'triceps', 'serratus anterior'],
  Pull: ['biceps', 'upper back', 'lats', 'forearms', 'spine', 'traps'],
  Legs: ['glutes', 'calves', 'quads', 'hamstrings', 'adductors', 'abductors'],
  Core: ['abs'],
  Other: ['cardiovascular system'],
}

const MUSCLE_LABELS = {
  pectorals: '胸肌', delts: '三角肌', triceps: '肱三头肌',
  'serratus anterior': '前锯肌',
  biceps: '肱二头肌', 'upper back': '上背', lats: '背阔肌',
  forearms: '前臂', spine: '脊柱', traps: '斜方肌',
  glutes: '臀肌', calves: '小腿', quads: '股四头肌',
  hamstrings: '腘绳肌', adductors: '内收肌', abductors: '外展肌',
  abs: '腹肌', 'levator scapulae': '提肩胛肌',
  'cardiovascular system': '有氧/心肺',
}

const CATEGORY_LABELS = { Push: '推', Pull: '拉', Legs: '腿', Core: '核心', Other: '其他' }

module.exports = {
  EXERCISE_INFO, CATEGORY_MUSCLE_MAP, MUSCLE_LABELS, CATEGORY_LABELS,
}
