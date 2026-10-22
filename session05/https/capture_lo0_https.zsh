#!/bin/zsh
# Lab 1 re-test: capture only NotesApp's loopback HTTPS traffic (lo0, TCP 443).
# dumpcap runs as root but writes to stdout, so the saved file belongs to the user
# and stays readable after Ctrl-C. It also stops on its own after 30 minutes.
set -eu
umask 077

capture_path="${0:A:h}/evidence/https-login-lo0-browser.pcapng"

if [[ -e "$capture_path" ]]; then
  print -u2 -r -- "文件已存在，已保留：$capture_path"
  print -u2 -r -- '请把这条提示发给我，不要删除或覆盖文件。'
  exit 1
fi

print -r -- '仅抓取本机 NotesApp 的 lo0 TCP 443 流量；登录完成后按 Ctrl-C 停止，最长 30 分钟。'
print -r -- '出现 Password 时，请本人输入 macOS 登录密码；输入时不会显示字符。'
sudo -v
sudo /opt/homebrew/bin/dumpcap -i lo0 -p \
  -f 'tcp port 443 and (host 127.0.0.1 or host ::1)' \
  -a duration:1800 -w - > "$capture_path"
