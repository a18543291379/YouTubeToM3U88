#!/bin/bash

# 安装 yt-dlp（如果未安装）
if ! command -v yt-dlp &> /dev/null; then
    echo "Installing yt-dlp..."
    pip install yt-dlp
fi

# 清空输出文件
echo "#EXTM3U" > youtube.m3u8
echo "" >> youtube.m3u8

# 读取 youtubeLink.txt
while IFS= read -r line; do
    # 跳过空行和注释
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # 解析字段
    channel_name=$(echo "$line" | awk -F '||' '{print $1}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    channel_id=$(echo "$line" | awk -F '||' '{print $2}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    category=$(echo "$line" | awk -F '||' '{print $3}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    url=$(echo "$line" | awk -F '||' '{print $4}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    if [[ -z "$channel_name" || -z "$channel_id" || -z "$url" ]]; then
        echo "跳过无效行: $line"
        continue
    fi

    echo "处理: $channel_name ($url)"
    stream_url=$(yt-dlp --no-cache-dir -g "$url" 2>/dev/null | head -1)
    if [[ -z "$stream_url" ]]; then
        echo "重试一次..."
        stream_url=$(yt-dlp --no-cache-dir -g "$url" 2>/dev/null | head -1)
    fi

    if [[ -z "$stream_url" ]]; then
        echo "❌ 无法获取流地址，跳过: $url"
        continue
    fi

    echo "#EXTINF:-1 tvg-id=\"$channel_id\" tvg-name=\"$channel_name\" group-title=\"$category\", $channel_name" >> youtube.m3u8
    echo "$stream_url" >> youtube.m3u8
    echo "" >> youtube.m3u8
    echo "✅ 已添加: $channel_name"
done < youtubeLink.txt

echo "✅ 生成完成！"
