# -*- coding: utf-8 -*-
"""
本地音乐播放器 + 在线歌词
=========================

功能：
  1. 扫描本地音乐文件夹（支持 mp3 / flac / wav / ogg），自动递归查找；
  2. 播放控制：播放 / 暂停 / 继续 / 上一首 / 下一首 / 进度拖拽 / 音量调节；
  3. 联网获取歌词：默认走网易云音乐网页接口，失败时自动切换 QQ 音乐接口；
  4. 歌词随播放进度同步高亮，并自动滚动到当前行。

运行：
  pip install pygame-ce
  python 本地音乐播放器.py

说明：
  - 歌词接口为公开网页接口，仅用于个人学习，请尊重音乐版权；
  - 找不到歌词时会明确提示，不影响正常播放；
  - 建议把文件名命名为「歌手 - 歌名.mp3」格式，歌词匹配更准确。
"""

import base64
import ctypes
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

try:
    import pygame
except Exception:
    pygame = None

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except Exception:
    Image = ImageDraw = ImageFont = ImageTk = None

MUSIC_EXTS = (".mp3", ".flac", ".wav", ".ogg", ".wma", ".aac", ".m4a", ".mp4", ".ape", ".wv", ".aiff", ".aif", ".opus")
DEFAULT_MUSIC_DIR = os.path.join(os.path.expanduser("~"), "Music")


# 网易云风格配色
ACCENT = "#1FD87A"          # Aurora 品牌绿
COVER_PLACEHOLDER = "#1E2E26"  # 深绿灰封面占位
SIDEBAR_BG = "#141419"      # Aurora 深色侧边栏
SIDEBAR_ACTIVE_BG = "#21212A"
MAIN_BG = "#0F0F12"         # Aurora 主背景
BAR_BG = "#141419"          # 底部播放栏
LYRIC_BG = "#0F0F12"        # 歌词面板背景（深色）
TEXT_DARK = "#EDEDF0"
TEXT_GRAY = "#8B8B97"
TEXT_DIM = "#6E6E7A"        # 次级灰
BORDER = "#1B1B21"          # 分隔线
CARD = "#1A1A20"            # 卡片/输入框底
ACTIVE_ROW = "#16241D"      # 播放行高亮
TITLE_BG = "#0F0F12"        # 标题栏背景

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

class LyricLine:
    """一行歌词：时间(毫秒) + 文本"""

    __slots__ = ("time_ms", "text")

    def __init__(self, time_ms, text):
        self.time_ms = time_ms
        self.text = text

def fmt_time(sec):
    sec = max(0, int(sec))
    return "%02d:%02d" % (sec // 60, sec % 60)

# ---------------- 音频时长解析（纯标准库，不依赖 pygame） ----------------

# MPEG 帧头 bitrate 表（kbps），键为 (版本, 层编码)。层编码：1=Layer III, 2=Layer II, 3=Layer I
MPEG_BITRATE = {
    (1, 1): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
    (1, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
    (1, 3): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
    (2, 1): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    (2, 3): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
    (25, 1): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    (25, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    (25, 3): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
}
MPEG_SAMPLE_RATE = {
    1: [44100, 48000, 32000],
    2: [22050, 24000, 16000],
    25: [11025, 12000, 8000],
}

def _mp3_duration_estimate(path):
    """按第一个 MP3 帧头估算时长（CBR 精确，VBR 近似）。"""
    try:
        with open(path, "rb") as f:
            head = f.read(10)
            if head[:3] == b"ID3":
                b = head[6:10]
                size = (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]
                f.seek(10 + size)
                head = f.read(4)
            if len(head) < 4 or head[0] != 0xFF or (head[1] & 0xE0) != 0xE0:
                return 0.0
            ver = {0b00: 25, 0b10: 2, 0b11: 1}.get((head[1] >> 3) & 0x03)
            layer = (head[1] >> 1) & 0x03
            if ver is None or layer == 0:
                return 0.0
            bitrate_idx = (head[2] >> 4) & 0x0F
            sr_idx = (head[2] >> 2) & 0x03
            if bitrate_idx in (0, 15) or sr_idx == 3:
                return 0.0
            bitrate = MPEG_BITRATE[(ver, layer)][bitrate_idx]
            sr = MPEG_SAMPLE_RATE[ver][sr_idx]
            if bitrate <= 0 or sr <= 0:
                return 0.0
            f.seek(0, 2)
            return f.tell() * 8.0 / (bitrate * 1000.0)
    except Exception:
        return 0.0

def _flac_duration(path):
    """解析 FLAC STREAMINFO，返回精确时长（秒）。"""
    try:
        with open(path, "rb") as f:
            data = f.read(42)
        if len(data) < 42 or data[:4] != b"fLaC" or (data[4] & 0x7F) != 0:
            return 0.0
        group = int.from_bytes(data[10:18], "big")
        sr = (group >> 44) & 0xFFFFF
        total = group & 0xFFFFFFFFF
        if sr <= 0 or total <= 0:
            return 0.0
        return total / sr
    except Exception:
        return 0.0

def _ogg_duration(path):
    """快速解析 OGG 时长：只读文件开头(采样率)和结尾(最后一个 OggS 页 granule)。"""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size < 64:
                return 0.0
            f.seek(0)
            head = f.read(131072)
            idx = head.find(b"\x01vorbis")
            if idx < 0 or len(head) < idx + 12:
                return 0.0
            sr = int.from_bytes(head[idx + 7:idx + 11], "little")
            if sr <= 0:
                return 0.0
            f.seek(max(0, size - 131072))
            tail = f.read(131072)
            pos = tail.rfind(b"OggS")
            if pos < 0 or len(tail) - pos < 27:
                return 0.0
            granule = int.from_bytes(tail[pos + 6:pos + 14], "little", signed=True)
            if granule <= 0:
                return 0.0
            return granule / sr
    except Exception:
        return 0.0

def get_duration_seconds(path):
    """获取音频时长（秒）；无法解析时返回 0。"""
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".wav":
            with __import__("wave").open(path, "rb") as w:
                return w.getnframes() / float(w.getframerate())
        if ext == ".flac":
            return _flac_duration(path)
        if ext == ".mp3":
            return _mp3_duration_estimate(path)
        if ext == ".ogg":
            return _ogg_duration(path)
        if ext in (".wma", ".aac", ".m4a", ".mp4", ".ape", ".wv",
                   ".aiff", ".aif", ".opus"):
            return _av_duration(path)
    except Exception:
        pass
    return 0.0

# ---------------- 全格式解码（PyAV 兜底） ----------------

_AV = None
def _av_module():
    """懒加载 PyAV；不可用时返回 False。"""
    global _AV
    if _AV is None:
        try:
            import av
            _AV = av
        except Exception:
            _AV = False
    return _AV

def _av_duration(path):
    """用 PyAV 读取音频时长（秒）；失败返回 0。"""
    av = _av_module()
    if not av:
        return 0.0
    try:
        with av.open(path) as c:
            d = c.duration
            return d / 1_000_000.0 if d else 0.0
    except Exception:
        return 0.0

def decode_to_wav(path, tmp_path):
    """用 PyAV 把任意格式音频解码为 16bit PCM WAV，写入 tmp_path。

    成功返回 True；失败清理临时文件并返回 False。
    """
    av = _av_module()
    if not av:
        return False
    w = None
    try:
        import wave
        container = av.open(path)
        stream = container.streams.audio[0]
        ctx = stream.codec_context
        rate = ctx.sample_rate or 44100
        ch = ctx.channels or 2
        w = wave.open(tmp_path, "wb")
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(rate)
        for frame in container.decode(audio=0):
            arr = frame.to_ndarray()
            if arr.dtype != "int16":
                arr = (arr * 32767.0).clip(-32768, 32767).astype("int16")
            if arr.ndim == 2:
                arr = arr.T          # (ch, n) -> (n, ch) 交错
            w.writeframes(arr.tobytes())
        w.close()
        w = None
        container.close()
        return True
    except Exception:
        if w is not None:
            try:
                w.close()
            except Exception:
                pass
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False

# ---------------- 专辑封面提取（纯标准库解析文件内嵌封面） ----------------

def _mp3_cover(path):
    """提取 MP3 ID3v2 APIC 帧中的封面图，返回图片字节；无则 None。"""
    try:
        with open(path, "rb") as f:
            head = f.read(10)
            if len(head) < 10 or head[:3] != b"ID3":
                return None
            ver = head[3]
            size = (head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9]
            if size <= 0:
                return None
            data = f.read(size)
        pos = 0
        while pos + 10 <= len(data):
            fid = data[pos:pos + 4]
            if fid == b"\x00" * 4:
                break
            raw_size = data[pos + 4:pos + 8]
            if ver == 4:  # ID3v2.4 帧长为同步安全整数
                fsize = ((raw_size[0] & 0x7F) << 21) | ((raw_size[1] & 0x7F) << 14) \
                        | ((raw_size[2] & 0x7F) << 7) | (raw_size[3] & 0x7F)
            else:
                fsize = int.from_bytes(raw_size, "big")
            if fsize <= 0:
                break
            body_start = pos + 10
            body = data[body_start:body_start + fsize]
            if fid == b"APIC" and len(body) > 4:
                enc = body[0]
                idx = 1
                mime_end = body.find(b"\x00", idx)
                if mime_end == -1:
                    return None
                idx = mime_end + 2      # 跳过 MIME 结束符与图片类型字节
                if idx >= len(body):
                    return None
                if enc in (1, 2):       # UTF-16 描述以 \x00\x00 结尾
                    desc_end = body.find(b"\x00\x00", idx)
                    idx = (desc_end + 2) if desc_end != -1 else len(body)
                else:
                    desc_end = body.find(b"\x00", idx)
                    idx = (desc_end + 1) if desc_end != -1 else len(body)
                if idx < len(body):
                    return body[idx:]
            pos = body_start + fsize
    except Exception:
        return None
    return None

def _extract_flac_picture(body):
    """从 FLAC PICTURE 块结构中取出图片字节。"""
    try:
        idx = 4
        mlen = int.from_bytes(body[idx:idx + 4], "big")
        idx += 4 + mlen
        dlen = int.from_bytes(body[idx:idx + 4], "big")
        idx += 4 + dlen
        idx += 16                       # width(4) height(4) depth(4) colors(4)
        datalen = int.from_bytes(body[idx:idx + 4], "big")
        idx += 4
        return body[idx:idx + datalen]
    except Exception:
        return None

def _flac_cover(path):
    """提取 FLAC 内嵌封面（METADATA_BLOCK_PICTURE，type 3 前置封面）。"""
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"fLaC":
                return None
            while True:
                hdr = f.read(4)
                if len(hdr) < 4:
                    return None
                last = hdr[0] & 0x80
                btype = hdr[0] & 0x7F
                blen = int.from_bytes(hdr[1:4], "big")
                if btype == 6:          # PICTURE 块
                    body = f.read(blen)
                    if len(body) >= 8 and int.from_bytes(body[0:4], "big") == 3:
                        return _extract_flac_picture(body)
                else:
                    f.seek(blen, 1)
                if last:
                    return None
    except Exception:
        return None
    return None

def _ogg_cover(path):
    """从 OGG vorbis 注释中提取 METADATA_BLOCK_PICTURE 封面。"""
    try:
        with open(path, "rb") as f:
            head = f.read(262144)
        marker = b"METADATA_BLOCK_PICTURE="
        pos = head.find(marker)
        if pos == -1:
            return None
        end = head.find(b"\x00", pos + len(marker))
        if end == -1:
            return None
        pic = base64.b64decode(head[pos + len(marker):end])
        return _extract_flac_picture(pic) if pic else None
    except Exception:
        return None

def get_embedded_cover(path):
    """按格式提取文件内嵌封面，返回图片字节；无封面返回 None。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mp3":
        return _mp3_cover(path)
    if ext == ".flac":
        return _flac_cover(path)
    if ext == ".ogg":
        return _ogg_cover(path)
    return None

# ---------------- 歌词：解析与联网获取 ----------------

def parse_lrc(lrc_text):
    """解析 LRC 歌词文本，返回按时间升序排列的 LyricLine 列表。

    支持 [offset:±ms] 全局偏移标签（正值=歌词整体提前）与 1/2/3 位小数。
    """
    offset_ms = 0
    for raw in lrc_text.splitlines()[:20]:
        mo = re.match(r"^\s*\[offset:\s*([+-]?\d+)\s*\]", raw, re.I)
        if mo:
            offset_ms = int(mo.group(1))
            break
    pattern = re.compile(r"\[(\d+):(\d+)(?:[.:](\d+))?\]")
    lines = []
    for raw in lrc_text.splitlines():
        matches = pattern.findall(raw)
        if not matches:
            continue
        text = pattern.sub("", raw).strip()
        if not text:
            continue
        for mm, ss, frac in matches:
            t = int(mm) * 60000 + int(ss) * 1000
            if frac:
                if len(frac) == 1:
                    t += int(frac) * 100
                elif len(frac) == 2:
                    t += int(frac) * 10
                else:
                    t += int(frac)
            t -= offset_ms
            lines.append(LyricLine(max(0, t), text))
    lines.sort(key=lambda x: x.time_ms)
    return lines

def _http_json(url, headers, timeout=6):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))

def _pick_best_song(songs, title, artist=""):
    """优先「歌名+歌手」精确匹配，其次歌名精确匹配，否则取第一个。

    兼容网易云(歌曲字段 name/artists) 与 QQ 音乐(歌曲字段 songname/singer)。
    """
    want = title.strip().lower()
    want_artist = artist.strip().lower()
    for s in songs:
        nm = str(s.get("name") or s.get("songname") or "").strip().lower()
        if nm != want:
            continue
        if want_artist:
            singers = s.get("singer") or s.get("artists") or []
            singer_str = ""
            if isinstance(singers, list):
                singer_str = " ".join(
                    str(x.get("name", "")) for x in singers if isinstance(x, dict))
            elif isinstance(singers, str):
                singer_str = singers
            elif isinstance(singers, dict):
                singer_str = str(singers.get("name", ""))
            if want_artist in singer_str.lower():
                return s
    for s in songs:
        nm = str(s.get("name") or s.get("songname") or "").strip().lower()
        if nm == want:
            return s
    return songs[0]

def _candidate_pairs(title, artist):
    """返回候选 (搜索词, 匹配歌名, 匹配歌手) 组合。

    兼容两种文件名格式：默认「歌手 - 歌名」，以及常见的
    「歌名 - 歌手」反格式（如"像我这样的人 - 毛不易.mp3"），
    并在组合失败时回退「仅歌名」「仅歌手」。
    """
    t = (title or "").strip()
    a = (artist or "").strip()
    pairs = []
    if t and a:
        pairs.append(("%s %s" % (t, a), t, a))
        if a != t:
            pairs.append(("%s %s" % (a, t), a, t))   # 反格式
    if t:
        pairs.append((t, t, ""))                      # 仅歌名
    if a and a != t:
        pairs.append((a, a, ""))                      # 仅歌手
    return pairs

def fetch_lyrics_netease(title, artist):
    """通过网易云音乐网页接口获取歌词，返回 LRC 文本；失败返回空串。"""
    headers = dict(BASE_HEADERS)
    headers["Referer"] = "https://music.163.com/"
    headers["Cookie"] = "os=pc; appver=2.0.2"

    song_id = None
    for query, q_title, q_artist in _candidate_pairs(title, artist):
        for tmpl in (
            "https://music.163.com/api/search/get/web?s={q}&type=1&limit=5&offset=0",
            "https://music.163.com/api/search/get?s={q}&type=1&limit=5&offset=0",
        ):
            try:
                data = _http_json(tmpl.format(q=urllib.parse.quote(query)), headers)
            except Exception:
                continue
            songs = ((data or {}).get("result") or {}).get("songs") or []
            if songs:
                song_id = _pick_best_song(songs, q_title, q_artist).get("id")
                break
        if song_id:
            break
    if not song_id:
        return ""
    try:
        data = _http_json(
            "https://music.163.com/api/song/lyric?id={}&lv=1&kv=1&tv=-1".format(song_id),
            headers,
        )
    except Exception:
        return ""
    return ((data or {}).get("lrc") or {}).get("lyric") or ""

def fetch_lyrics_qq(title, artist):
    """通过 QQ 音乐网页接口获取歌词，返回 LRC 文本；失败返回空串。"""
    headers = dict(BASE_HEADERS)
    headers["Referer"] = "https://y.qq.com/"
    songmid = None
    for query, q_title, q_artist in _candidate_pairs(title, artist):
        try:
            data = _http_json(
                "https://c.y.qq.com/soso/fcgi-bin/client_search_cp?"
                "p=1&n=5&w={}&format=json".format(urllib.parse.quote(query)),
                headers,
            )
        except Exception:
            continue
        songs = ((data or {}).get("data") or {}).get("song") or {}
        song_list = songs.get("list") or []
        if song_list:
            songmid = _pick_best_song(song_list, q_title, q_artist).get("songmid")
        if songmid:
            break
    if not songmid:
        return ""
    try:
        data = _http_json(
            "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?"
            "songmid={}&format=json&nobase64=1".format(songmid),
            headers,
        )
    except Exception:
        return ""
    return data.get("lyric") or ""

def fetch_lyrics(title, artist):
    """依次尝试网易云、QQ 音乐获取歌词，返回 (LRC文本, 来源名)。

    仅当返回文本包含 [mm:ss] 时间轴歌词行时才算有效，避免
    [ti:]/[ar:] 等只有元数据、没有实际歌词的"空壳歌词"。
    """
    for fn, name in (
        (fetch_lyrics_netease, "网易云音乐"),
        (fetch_lyrics_qq, "QQ音乐"),
    ):
        try:
            lrc = fn(title, artist)
        except Exception:
            continue
        if lrc and re.search(r"\[\d+:\d+", lrc):
            return lrc, name
    return "", ""

# ---------------- 封面：联网抓取 ----------------

def _download_image(url, referer=None):
    headers = {"User-Agent": BASE_HEADERS["User-Agent"]}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read()
    return data if data and len(data) > 100 else None

def fetch_online_cover(title, artist):
    """按 歌手-歌名 从 QQ 音乐搜索专辑并下载封面，返回图片字节；失败返回 None。"""
    query = ("%s %s" % (title, artist)).strip()
    headers = dict(BASE_HEADERS)
    headers["Referer"] = "https://y.qq.com/"
    try:
        data = _http_json(
            "https://c.y.qq.com/soso/fcgi-bin/client_search_cp?"
            "p=1&n=8&w={}&format=json".format(urllib.parse.quote(query)),
            headers,
        )
    except Exception:
        return None
    songs = (((data or {}).get("data") or {}).get("song") or {}).get("list") or []
    if not songs:
        return None
    song = _pick_best_song(songs, title)
    urls = []
    if song.get("albummid"):
        urls.append("https://y.gtimg.cn/music/photo_new/T002R300x300M000%s.jpg" % song["albummid"])
    if song.get("albumid"):
        urls.append("https://imgcache.qq.com/music/photo/album_300/%s/300_albumpic_%s_0.jpg"
                    % (song["albumid"], song["albumid"]))
    for u in urls:
        try:
            img = _download_image(u, referer="https://y.qq.com/")
            if img:
                return img
        except Exception:
            continue
    return None

# ---------------- 细滚动条（参考图样式：无箭头、扁平细条） ----------------

class SlimScrollbar(tk.Canvas):
    """参照截图的细滚动条：窄条轨道 + 浅色滑块，无上下箭头。"""

    def __init__(self, parent, command=None, width=6, **kw):
        super().__init__(parent, width=width, bg=parent["bg"],
                         highlightthickness=0, bd=0, **kw)
        self._command = command
        self._frac = 1.0          # 可见比例（0..1）
        self._start = 0.0         # 滑块起始比例
        self._thumb_y = 0
        self._thumb_h = 0
        self._drag_off = 0
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", lambda _e: self._redraw())
        self.bind("<Leave>", lambda _e: self._redraw())

    def set(self, lo, hi):
        try:
            lo, hi = float(lo), float(hi)
        except Exception:
            return
        self._frac = 1.0 if hi <= lo else max(0.0, min(1.0, hi - lo))
        self._redraw()

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if h <= 2:
            return
        track = "#D12F2F"      # 轨道：比红色背景深一档
        thumb = "#FFE3E3"      # 滑块：浅色（参照图浅灰滑块）
        self.create_rectangle(2, 1, w - 1, h - 1, fill=track, outline="")
        th = max(24, int(h * self._frac))
        max_y = h - th
        ty = int(self._start * max(1, max_y))
        ty = max(1, min(max_y, ty))
        self._thumb_y, self._thumb_h = ty, th
        self.create_rectangle(3, ty + 2, w - 2, ty + th - 2,
                              fill=thumb, outline="")

    def _on_press(self, event):
        h = self.winfo_height()
        if h <= 2 or self._thumb_h <= 0:
            return
        if event.y < self._thumb_y:
            self._command("scroll", -1, "pages")
        elif event.y > self._thumb_y + self._thumb_h:
            self._command("scroll", 1, "pages")
        else:
            self._drag_off = event.y - self._thumb_y

    def _on_drag(self, event):
        h = self.winfo_height()
        if h <= self._thumb_h or self._thumb_h <= 0:
            return
        frac = (event.y - self._drag_off) / max(1, h - self._thumb_h)
        frac = max(0.0, min(1.0, frac))
        self._start = frac
        self._command("moveto", frac)
        self._redraw()

# ---------------- 高清图标：4x 超采样渲染 PNG（拖拽窗口不失真） ----------------

_ICON_FONT_CACHE = {}

def _icon_font(size):
    """取高清数字/文字图标字体（粗体优先，带缓存）。"""
    if size not in _ICON_FONT_CACHE:
        fonts = []
        windir = os.environ.get("WINDIR", r"C:\Windows")
        for name in ("arialbd.ttf", "arial.ttf", "segoeuib.ttf", "segoeui.ttf"):
            fonts.append(os.path.join(windir, "Fonts", name))
        fonts.append(os.path.join(windir, "Fonts", "seguisym.ttf"))
        fonts.append("arial.ttf")
        f = None
        for path in fonts:
            try:
                f = ImageFont.truetype(path, size)
                break
            except Exception:
                continue
        if f is None:
            f = ImageFont.load_default()
        _ICON_FONT_CACHE[size] = f
    return _ICON_FONT_CACHE[size]

def _pil_icon(size, draw):
    """按 4x 超采样绘制图标，LANCZOS 缩回目标尺寸（边缘平滑的高清图）。"""
    S = max(8, size * 4)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw(d, S)
    return img.resize((size, size), Image.LANCZOS)

def _tri_pil(d, x, y, direction, s, col):
    """PIL 三角形：direction<0 向左，>0 向右。"""
    if direction < 0:
        d.polygon([(x + s, y - s), (x + s, y + s), (x - s, y)], fill=col)
    else:
        d.polygon([(x - s, y - s), (x - s, y + s), (x + s, y)], fill=col)

def _draw_icon_play(d, S, playing, hover):
    """圆形播放/暂停：Aurora 绿底（悬停亮绿）+ 深色 ▶ / ❚❚。"""
    cx = cy = S / 2.0
    pad = S * 0.045
    r = S / 2.0 - pad
    d.ellipse([pad, pad, S - pad, S - pad],
              fill="#35E88C" if hover else ACCENT)
    col = "#0B1A12"
    if playing:
        bw = r * 0.22
        gap = r * 0.34
        for dx in (-gap, gap):
            d.rectangle([cx + dx - bw / 2.0, cy - r * 0.42,
                         cx + dx + bw / 2.0, cy + r * 0.42], fill=col)
    else:
        d.polygon([(cx - r * 0.34, cy - r * 0.44),
                   (cx + r * 0.48, cy),
                   (cx - r * 0.34, cy + r * 0.44)], fill=col)

def _draw_icon_arrow(d, S, direction, bg):
    """上一曲/下一曲：浅红圆底 + 白色 ⏮/⏭（双三角 + 竖杠）。"""
    cx = cy = S / 2.0
    d.ellipse([S * 0.03, S * 0.03, S * 0.97, S * 0.97], fill=bg)
    col = "#FFFFFF"
    s = S * 0.115
    bar = S * 0.05
    if direction < 0:   # ⏮
        _tri_pil(d, cx - S * 0.16, cy, -1, s, col)
        _tri_pil(d, cx + S * 0.02, cy, -1, s, col)
        d.rectangle([cx + S * 0.21, cy - S * 0.17,
                     cx + S * 0.21 + bar, cy + S * 0.17], fill=col)
    else:               # ⏭
        d.rectangle([cx - S * 0.21 - bar, cy - S * 0.17,
                     cx - S * 0.21, cy + S * 0.17], fill=col)
        _tri_pil(d, cx - S * 0.02, cy, 1, s, col)
        _tri_pil(d, cx + S * 0.16, cy, 1, s, col)

def _draw_icon_mode(d, S, mode):
    """播放模式图标（Feather 线框风，缩小为原尺寸一半）：
    list=双环箭头(repeat) / single=双环箭头+中央1 / shuffle=交叉箭头。"""
    col = "#FFFFFF"
    w = max(2, int(S / 24.0 * 2))   # 对应 Feather stroke-width=2/24
    k = 0.5                         # 整体缩小一半（居中）

    def P(x, y):
        return (x - 12.0) * S / 24.0 * k + S / 2.0, (y - 12.0) * S / 24.0 * k + S / 2.0

    if mode in ("list", "single"):
        # 上弧线：左竖线 → 左上 90° 弧 → 上横线
        d.line([P(3, 11), P(3, 9)], fill=col, width=w)
        d.arc([P(3, 5), P(11, 13)], start=180, end=270, fill=col, width=w)
        d.line([P(7, 5), P(21, 5)], fill=col, width=w)
        # 右上箭头（V 形，顶点朝右）
        d.line([P(17, 1), P(21, 5)], fill=col, width=w)
        d.line([P(21, 5), P(17, 9)], fill=col, width=w)
        # 下弧线：右竖线 → 右下 90° 弧 → 下横线
        d.line([P(21, 13), P(21, 15)], fill=col, width=w)
        d.arc([P(13, 11), P(21, 19)], start=0, end=90, fill=col, width=w)
        d.line([P(17, 19), P(3, 19)], fill=col, width=w)
        # 左下箭头（V 形，顶点朝左）
        d.line([P(7, 23), P(3, 19)], fill=col, width=w)
        d.line([P(3, 19), P(7, 15)], fill=col, width=w)
        if mode == "single":
            f = _icon_font(int(S * 0.15))
            tb = d.textbbox((0, 0), "1", font=f)
            tw, th = tb[2] - tb[0], tb[3] - tb[1]
            d.text((S / 2.0 - tw / 2.0, S / 2.0 - th / 2.0 - tb[1]), "1",
                   font=f, fill=col)
    else:  # shuffle：两条交叉斜线 + 左上/右下钩（Feather shuffle）
        def L(p1, p2):
            d.line([P(*p1), P(*p2)], fill=col, width=w)
        L((16, 3), (21, 3)); L((21, 3), (21, 8))
        L((21, 16), (21, 21)); L((21, 21), (16, 21))
        L((15, 15), (21, 21))
        L((4, 4), (9, 9))
        L((4, 20), (21, 3))

def _draw_icon_heart(d, S, filled):
    """收藏图标：♡ 空心（未收藏）/ ♥ 实心（已收藏，绿色）。"""
    ch = "\u2665" if filled else "\u2661"
    f = _icon_font(int(S * 0.66))
    tb = d.textbbox((0, 0), ch, font=f)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    d.text((S / 2 - tw / 2, S / 2 - th / 2 - tb[1]), ch, font=f,
           fill=(ACCENT if filled else "#EDEDF0"))


def _draw_icon_list(d, S):
    """播放列表图标：三横线 + 三个圆点（Feather list）。"""
    col = "#EDEDF0"
    w = max(2, int(S * 0.075))
    for y in (7, 12, 17):
        yy = S * y / 24
        d.line([S * 0.30, yy, S * 0.88, yy], fill=col, width=w)
        d.ellipse([S * 0.20 - w / 2, yy - w / 2, S * 0.20 + w / 2, yy + w / 2], fill=col)


def _draw_icon_cover(d, S):
    """封面源图标：相框 + 太阳 + 山（Feather image）。"""
    col = "#EDEDF0"
    w = max(2, int(S * 0.07))
    d.rectangle([S * 0.14, S * 0.14, S * 0.86, S * 0.86], outline=col, width=w)
    d.ellipse([S * 0.34, S * 0.30, S * 0.44, S * 0.40], outline=col, width=w)
    d.line([S * 0.20, S * 0.72, S * 0.42, S * 0.44], fill=col, width=w)
    d.line([S * 0.42, S * 0.44, S * 0.62, S * 0.62], fill=col, width=w)
    d.line([S * 0.62, S * 0.62, S * 0.84, S * 0.38], fill=col, width=w)


def _draw_icon_speaker(d, S, col="#FFFFFF"):
    """喇叭图标：箱体 + 声波弧线。"""
    cx = S * 0.32
    d.polygon([(cx - S * 0.20, S * 0.32), (cx - S * 0.04, S * 0.32),
               (cx + S * 0.12, S * 0.20), (cx + S * 0.12, S * 0.80),
               (cx - S * 0.04, S * 0.68), (cx - S * 0.20, S * 0.68)], fill=col)
    d.arc([cx + S * 0.10, S * 0.30, cx + S * 0.34, S * 0.70],
          start=-55, end=55, fill=col, width=max(2, int(S * 0.045)))
    d.arc([cx + S * 0.16, S * 0.22, cx + S * 0.46, S * 0.78],
          start=-55, end=55, fill=col, width=max(2, int(S * 0.045)))

class ModeIconButton(tk.Canvas):
    """播放模式图标按钮（高清图）：环形箭头 / 环形箭头+1 / 交叉箭头。"""

    def __init__(self, parent, mode="list", command=None, size=44, **kw):
        super().__init__(parent, width=size, height=size, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._mode = mode
        self._command = command
        self._imgs = {}
        self.bind("<Button-1>", self._on_click)
        self.bind("<Configure>", lambda _e: self._draw())

    def set_mode(self, mode):
        self._mode = mode
        self._draw()

    def _on_click(self, _event):
        if self._command:
            self._command()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2:
            return
        size = max(4, int(min(w, h)))
        key = (size, self._mode)
        if key not in self._imgs:
            self._imgs[key] = ImageTk.PhotoImage(
                _pil_icon(size, lambda d, S: _draw_icon_mode(d, S, self._mode)))
        self.create_image(w / 2.0, h / 2.0, image=self._imgs[key])

class VolumeSlider(tk.Canvas):
    """竖向音量滑杆：白色轨道 + 青绿色填充 + 圆形滑块（参照图样式）。"""

    def __init__(self, parent, value=70, command=None, height=170, width=22, **kw):
        super().__init__(parent, width=width, height=height, bg="#FFFFFF",
                         highlightthickness=0, bd=0, **kw)
        self._value = max(0, min(100, value))
        self._command = command
        self._drag_off = 0
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Configure>", lambda _e: self._redraw())

    def set_value(self, v):
        self._value = max(0, min(100, v))
        self._redraw()

    def _track_h(self):
        return max(2, self.winfo_height() - 20)

    def _value_y(self):
        h = self._track_h()
        return 10 + int((100 - self._value) * (h - 1) / 100.0)

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if h <= 2:
            return
        track_h = self._track_h()
        x0, x1 = w // 2 - 4, w // 2 + 4
        self.create_rectangle(x0, 10, x1, 10 + track_h, fill="#EDEDED", outline="#DCDCDC")
        if self._value > 0:
            yv = self._value_y()
            self.create_rectangle(x0, yv, x1, 10 + track_h, fill=ACCENT, outline="")
        yv = self._value_y()
        self.create_oval(x0 - 4, yv - 4, x1 + 4, yv + 4, fill="#FFFFFF",
                         outline="#B8B8B8", width=1)

    def _set_from_y(self, y):
        h = self._track_h()
        frac = (10 + h - y) / max(1, h)
        v = max(0, min(100, int(round(frac * 100))))
        if v != self._value:
            self._value = v
            if self._command:
                self._command(v)
            self._redraw()

    def _on_press(self, event):
        self._set_from_y(event.y)
        self._drag_off = event.y - self._value_y()

    def _on_drag(self, event):
        self._set_from_y(event.y - self._drag_off)

    def _on_wheel(self, event):
        delta = -5 if event.delta > 0 else 5
        v = max(0, min(100, self._value + delta))
        if v != self._value:
            self._value = v
            if self._command:
                self._command(v)
            self._redraw()

class PlayButton(tk.Canvas):
    """圆形播放/暂停按钮（高清图）：白底红图标，点击切换。"""

    def __init__(self, parent, command=None, size=50, color=ACCENT, **kw):
        super().__init__(parent, width=size, height=size, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._playing = False
        self._hover = False
        self._color = color
        self._command = command
        self._imgs = {}
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Configure>", lambda _e: self._draw())

    def set_playing(self, playing):
        self._playing = playing
        self._draw()

    def _set_hover(self, hover):
        self._hover = hover
        self._draw()

    def _on_click(self, _event):
        if self._command:
            self._command()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2:
            return
        size = max(4, int(min(w, h)))
        key = (size, self._playing, self._hover)
        if key not in self._imgs:
            self._imgs[key] = ImageTk.PhotoImage(
                _pil_icon(size, lambda d, S: _draw_icon_play(d, S, self._playing, self._hover)))
        self.create_image(w / 2.0, h / 2.0, image=self._imgs[key])

class RoundIconButton(tk.Canvas):
    """上一曲/下一曲按钮（高清图）：半透明圆底白图标，悬停加深。"""

    def __init__(self, parent, icon, command=None, width=56, height=44, **kw):
        super().__init__(parent, width=width, height=height, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._icon = icon            # "prev" / "next"
        self._command = command
        self._hover = False
        self._imgs = {}
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Configure>", lambda _e: self._draw())

    def _set_hover(self, hover):
        self._hover = hover
        self._draw()

    def _on_click(self, _event):
        if self._command:
            self._command()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2:
            return
        size = max(4, int(min(w, h)))
        key = (size, self._icon, self._hover)
        if key not in self._imgs:
            bg = "#35E88C" if self._hover else ACCENT
            direction = -1 if self._icon == "prev" else 1
            self._imgs[key] = ImageTk.PhotoImage(
                _pil_icon(size, lambda d, S: _draw_icon_arrow(d, S, direction, bg)))
        self.create_image(w / 2.0, h / 2.0, image=self._imgs[key])

class ImageIconButton(tk.Canvas):
    """通用高清图标按钮：透明底白色图标，悬停显示浅红圆底。"""

    def __init__(self, parent, draw, command=None, size=40, **kw):
        super().__init__(parent, width=size, height=size, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2", **kw)
        self._draw_fn = draw
        self._command = command
        self._hover = False
        self._imgs = {}
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Configure>", lambda _e: self._draw())

    def _set_hover(self, hover):
        self._hover = hover
        self._draw()

    def _on_click(self, _event):
        if self._command:
            self._command()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2:
            return
        size = max(4, int(min(w, h)))
        key = (size, self._hover)
        if key not in self._imgs:
            def painter(d, S):
                if self._hover:
                    d.ellipse([S * 0.03, S * 0.03, S * 0.97, S * 0.97], fill=ACCENT)
                self._draw_fn(d, S)
            self._imgs[key] = ImageTk.PhotoImage(_pil_icon(size, painter))
        self.create_image(w / 2.0, h / 2.0, image=self._imgs[key])

class MarqueeLabel(tk.Canvas):
    """左右滚动歌名标签：文字超宽时横向循环滚动，宽度内文字静止显示。"""

    def __init__(self, parent, bg, fg, font, width=178, height=20, root=None, **kw):
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0,
                         width=width, height=height, **kw)
        self._fg = fg
        self._font = font
        self._root = root
        self._text = ""
        self._x = 0
        self._full = ""
        self._total = 0
        self._after = None

    def set_text(self, text):
        text = text or ""
        if text == self._text:
            return
        self._text = text
        self._stop()
        self.delete("all")
        self._x = 0
        if not text:
            return
        f = tkfont.Font(root=self._root, font=self._font)
        w = max(20, self.winfo_width() or 178)
        tw = f.measure(text)
        if tw <= w:
            self.create_text(0, (self.winfo_height() or 20) / 2.0,
                             anchor="w", text=text, fill=self._fg, font=self._font)
            return
        # 超宽 → 文本 + 间隔 + 文本，循环向左滚动
        self._gap = f.measure("    ")
        self._full = text + "    " + text
        self._total = tw + self._gap
        self._tick()

    def _tick(self):
        self.delete("all")
        self.create_text(-self._x, (self.winfo_height() or 20) / 2.0,
                         anchor="w", text=self._full, fill=self._fg, font=self._font)
        self._x += 1
        if self._x >= self._total:
            self._x = 0
        self._after = self._root.after(20, self._tick)

    def _stop(self):
        if self._after is not None:
            try:
                self._root.after_cancel(self._after)
            except Exception:
                pass
            self._after = None

class WebProgressBar(tk.Canvas):
    """播放器样式进度条：细线轨道 + 白色已播放段 + 悬停圆点（纯色，无绿色）。"""

    TRACK_HOVER_H = 5      # 悬停时轨道高度
    TRACK_H = 3            # 平时轨道高度
    DOT_R = 5              # 圆点半径（直径 10px）
    RADIUS = 2             # 圆角半径

    def __init__(self, master, command=None, bg="#141419", **kw):
        super().__init__(master, bg=bg, highlightthickness=0, bd=0,
                         height=18, cursor="hand2", **kw)
        self._command = command        # 回调(比例, final)
        self._ratio = 0.0
        self._hover = False
        self._dragging = False
        self._bar_h = self.TRACK_H
        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw()

    def set_ratio(self, ratio):
        r = max(0.0, min(1.0, float(ratio)))
        if abs(r - self._ratio) > 1e-4:
            self._ratio = r
            self._redraw()

    def _on_enter(self, _e):
        self._hover = True
        self._bar_h = self.TRACK_HOVER_H
        self._redraw()

    def _on_leave(self, _e):
        self._hover = False
        self._bar_h = self.TRACK_H
        self._redraw()

    def _ratio_of(self, event):
        w = self.winfo_width()
        if w <= 1:
            return 0.0
        return max(0.0, min(1.0, event.x / float(w)))

    def _on_press(self, e):
        self._dragging = True
        self._ratio = self._ratio_of(e)
        self._redraw()
        if self._command:
            self._command(self._ratio, False)

    def _on_drag(self, e):
        if self._dragging:
            self._ratio = self._ratio_of(e)
            self._redraw()
            if self._command:
                self._command(self._ratio, False)

    def _on_release(self, e):
        if self._dragging:
            self._ratio = self._ratio_of(e)
            self._redraw()
            if self._command:
                self._command(self._ratio, True)
        self._dragging = False

    @staticmethod
    def _mix_white_alpha(rgb, alpha):
        """在 rgb 底色上叠加 alpha 的白，模拟半透明。"""
        return tuple(int(c + (255 - c) * alpha) for c in rgb)

    def _rounded(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
               x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
               x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return
        cy = h / 2.0
        track_r = 2
        bh = self._bar_h
        y1 = cy - bh / 2.0
        y2 = cy + bh / 2.0

        track = self._mix_white_alpha((0x14, 0x14, 0x19), 0.30)
        self._rounded(0, y1, w, y2, track_r, fill="#%02X%02X%02X" % track,
                      outline="")

        fw = w * self._ratio
        if fw > 0.5:
            self._rounded(0, y1, fw, y2, track_r, fill="white", outline="")

        if self._hover and fw > 0.5:
            x = fw
            self.create_oval(x - self.DOT_R, cy - self.DOT_R,
                             x + self.DOT_R, cy + self.DOT_R,
                             fill="white", outline="#2E2E33", width=1)
