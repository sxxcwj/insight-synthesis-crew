#!/bin/bash
# 长伴咨询 · 公网安全访问隧道启动脚本
# 默认映射 4A 旗舰控制台 (8000)，也可传参指定端口（如 8501）

PORT=${1:-8000}
BIN_DIR="$(cd "$(dirname "$0")" && pwd)/bin"

if [ ! -f "$BIN_DIR/cloudflared" ]; then
    echo "❌ 未检测到 cloudflared 二进制文件，正在自动下载..."
    mkdir -p "$BIN_DIR"
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz | tar -xz -C "$BIN_DIR"
    chmod +x "$BIN_DIR/cloudflared"
fi

echo "🚀 正在为本地端口 $PORT 建立公网安全隧道 (HTTPS)..."
"$BIN_DIR/cloudflared" tunnel --protocol http2 --url "http://localhost:$PORT"
