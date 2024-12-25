#!/bin/bash
# 定义旧的和新的 IP 地址
OLD_IP="10.32.68.67"
NEW_IP="10.32.98.215"

# 替换文件中的 IP 地址
replace_ip_in_file() {
    local file_path=$1
    local old_ip=$2
    local new_ip=$3

    if [[ -f $file_path ]]; then
        sed -i "s/$old_ip/$new_ip/g" "$file_path"
        echo "已成功替换 $file_path 中的 IP 地址"
    else
        echo "文件 $file_path 不存在"
    fi
}

# 修改 Server/config.py 中的 SERVER_IP
replace_ip_in_file "Server/config.py" "$OLD_IP" "$NEW_IP"

# 修改 Client/config.py 中的 SERVER_IP_LOGIC
replace_ip_in_file "Client/config.py" "$OLD_IP" "$NEW_IP"

# 修改 conference.vue 中的 this.socket URL
replace_ip_in_file "src/pages/conference.vue" "$OLD_IP" "$NEW_IP"

# 修改 mode.vue 中的 this.socket URL
replace_ip_in_file "src/pages/mode.vue" "$OLD_IP" "$NEW_IP"

echo "IP 地址已成功替换为 $NEW_IP"