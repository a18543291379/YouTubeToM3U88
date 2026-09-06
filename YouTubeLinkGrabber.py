#!/usr/bin/env python3
import os
from datetime import datetime, timedelta

import pytz
import requests
from lxml import etree
from bs4 import BeautifulSoup

tz = pytz.timezone('Europe/London')
channels = []


def generate_times(curr_dt: datetime):
    """
    Generate 3-hourly blocks of times based on a current date
    """
    last_hour = curr_dt.replace(microsecond=0, second=0, minute=0)
    last_hour = tz.localize(last_hour)
    start_dates = [last_hour]

    for x in range(7):
        last_hour += timedelta(hours=3)
        start_dates.append(last_hour)

    end_dates = start_dates[1:]
    end_dates.append(start_dates[-1] + timedelta(hours=3))
    return start_dates, end_dates


def build_xml_tv(streams: list) -> bytes:
    """Build XMLTV file based on stream info"""
    data = etree.Element("tv")
    data.set("generator-info-name", "youtube-live-epg")
    data.set("generator-info-url", "https://github.com/dp247/YouTubeToM3U8")

    for stream in streams:
        channel = etree.SubElement(data, "channel")
        channel.set("id", stream[1])
        name = etree.SubElement(channel, "display-name")
        name.set("lang", "en")
        name.text = stream[0]

        dt_format = '%Y%m%d%H%M%S %z'
        start_dates, end_dates = generate_times(datetime.now())

        for idx, val in enumerate(start_dates):
            programme = etree.SubElement(data, 'programme')
            programme.set("channel", stream[1])
            programme.set("start", val.strftime(dt_format))
            programme.set("stop", end_dates[idx].strftime(dt_format))

            title = etree.SubElement(programme, "title")
            title.set('lang', 'en')
            title.text = stream[3] if stream[3] != '' else f'LIVE: {stream[0]}'
            description = etree.SubElement(programme, "desc")
            description.set('lang', 'en')
            description.text = stream[4] if stream[4] != '' else 'No description provided'
            icon = etree.SubElement(programme, "icon")
            icon.set('src', stream[5])

    return etree.tostring(data, pretty_print=True, encoding='utf-8')


def grab(url: str, channel_name: str, channel_id: str, category: str):
    """
    Grabs the live-streaming M3U8 URL from a YouTube livestream page.
    """
    if '&' in url:
        url = url.split('&')[0]

    requests.packages.urllib3.disable_warnings()
    try:
        stream_info = requests.get(url, timeout=15)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return

    response = stream_info.text
    soup = BeautifulSoup(stream_info.text, features="html.parser")

    # 检查响应中是否包含 .m3u8
    if '.m3u8' not in response or stream_info.status_code != 200:
        print(f"❌ 未找到 M3U8 流: {url}")
        return

    end = response.find('.m3u8') + 5
    tuner = 100
    while True:
        if 'https://' in response[end - tuner: end]:
            link = response[end - tuner: end]
            start = link.find('https://')
            end = link.find('.m3u8') + 5
            stream_url = link[start: end]

            # 获取页面元数据
            stream_title = soup.find("meta", property="og:title")
            stream_desc = soup.find("meta", property="og:description")
            stream_image = soup.find("meta", property="og:image")
            stream_title = stream_title["content"] if stream_title else channel_name
            stream_desc = stream_desc["content"] if stream_desc else ''
            stream_image_url = stream_image["content"] if stream_image else ''

            channels.append((channel_name, channel_id, category, stream_title, stream_desc, stream_image_url))
            print(f"{stream_url}")
            break
        else:
            tuner += 5
            if tuner > 500:
                print(f"❌ 无法提取流地址: {url}")
                break


# ========== 主流程：读取 youtubeLink.txt ==========
print("#EXTM3U")

with open('./youtubeLink.txt', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('##'):
            continue
        # 如果行中包含 '||'，说明是频道信息行
        if '||' in line:
            parts = line.split('||')
            if len(parts) >= 4:
                channel_name = parts[0].strip()
                channel_id = parts[1].strip()
                category = parts[2].strip().title()
                url = parts[3].strip()
                # 打印 EXTINF 行（先不输出 URL，因为 URL 可能变化）
                print(f'\n#EXTINF:-1 tvg-id="{channel_id}" tvg-name="{channel_name}" group-title="{category}", {channel_name}')
                # 调用 grab 获取真实流地址并输出
                grab(url, channel_name, channel_id, category)
        else:
            # 如果行是纯 URL（但按照新格式不应该出现）
            print(f"# 跳过未识别的行: {line}")

# 生成 EPG 文件（如果 channels 非空）
if channels:
    channel_xml = build_xml_tv(channels)
    with open('epg.xml', 'wb') as f:
        f.write(channel_xml)
        print("✅ EPG 生成完成")

# 清理临时文件（如果有）
if 'temp.txt' in os.listdir():
    os.system('rm temp.txt')
    if 'watch*' in os.listdir():
        os.system('rm watch*')
