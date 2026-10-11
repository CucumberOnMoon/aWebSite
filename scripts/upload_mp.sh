#!/usr/bin/env bash
# 上传微信小程序（miniprogram-ci）
# 用法: scripts/upload_mp.sh <版本号> "<描述>" [robot 1-30]
# 密钥: 默认 $HOME/.mp-keys/private.wx06ccc7d635a3bdc0.key，可用 WX_UPLOAD_KEY 覆盖
set -euo pipefail

APPID="wx06ccc7d635a3bdc0"
PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../miniprogram" && pwd)"
KEY="${WX_UPLOAD_KEY:-$HOME/.mp-keys/private.wx06ccc7d635a3bdc0.key}"
CI="${MP_CI_BIN:-$HOME/mp-ci/node_modules/.bin/miniprogram-ci}"
[ -x "$CI" ] || CI="/usr/local/bin/miniprogram-ci"
# 微信 CI 的 IP 白名单按 IPv4 校验，强制 node 走 IPv4 出口
export NODE_OPTIONS="--dns-result-order=ipv4first ${NODE_OPTIONS:-}"
ROBOT="${3:-1}"
VER="${1:?用法: upload_mp.sh <版本号> <描述> [robot]}"
DESC="${2:-auto upload}"

[ -f "$KEY" ] || { echo "❌ 上传密钥不存在: $KEY" >&2; exit 1; }
[ -f "$PROJ/app.json" ] || { echo "❌ 小程序目录不对: $PROJ" >&2; exit 1; }

# .bak / 备份文件会被打包进去，上传前清掉
find "$PROJ" -type f \( -name '*.bak' -o -name '*.bak.*' \) -print -delete

echo "▶ 上传 $APPID  ver=$VER robot=$ROBOT"
exec "$CI" upload \
  --pp "$PROJ" --pkp "$KEY" --appid "$APPID" \
  --uv "$VER" --ud "$DESC" -r "$ROBOT" --use-cos
