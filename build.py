# -*- coding: utf-8 -*-
"""合并分片源码，生成完整的《本地音乐播放器.py》。

用法：
    python build.py

生成文件：
    本地音乐播放器.py（part1 + part2 拼接，可直接运行）
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = ["本地音乐播放器_part1.py", "本地音乐播放器_part2.py"]
OUT = "本地音乐播放器.py"


def main():
    chunks = []
    for name in PARTS:
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            print("缺少文件:", p)
            return 1
        with open(p, "r", encoding="utf-8") as f:
            chunks.append(f.read())
    out_path = os.path.join(HERE, OUT)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(chunks))
    print("OK ->", OUT, os.path.getsize(out_path), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
