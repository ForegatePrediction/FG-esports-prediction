#!/usr/bin/env python3
"""
下载 Oracle's Elixir 逐场比赛 CSV(免费,官方 Google Drive 每日更新)。
自动从公开文件夹列出各年份文件的最新 ID(对 ID 变动更稳健),再下载指定年份。

用法:
    python3 data/fetch.py               # 下载 2024 2025 2026
    python3 data/fetch.py 2025 2026     # 指定年份
"""
import re, sys, os, urllib.request, datetime
from html.parser import HTMLParser

FOLDER_ID = "1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH"   # OE 官方 Downloads 文件夹
HERE = os.path.dirname(os.path.abspath(__file__))


class FolderParser(HTMLParser):
    """Read entry/title elements without depending on HTML spacing or attribute order."""
    def __init__(self):
        super().__init__()
        self.file_id = None
        self.title = False
        self.files = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id", "").startswith("entry-"):
            self.file_id = attrs["id"][6:]
        if "flip-entry-title" in attrs.get("class", "").split():
            self.title = True

    def handle_endtag(self, tag):
        self.title = False

    def handle_data(self, data):
        match = re.match(r"(\d{4})_LoL", data.strip()) if self.title else None
        if match and self.file_id:
            self.files[match[1]] = self.file_id


def list_folder():
    url = f"https://drive.google.com/embeddedfolderview?id={FOLDER_ID}#list"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as response:
        html = response.read().decode("utf-8")
    parser = FolderParser()
    parser.feed(html)
    if not parser.files:
        raise RuntimeError("Oracle's Elixir 年度文件列表为空，拒绝继续")
    return parser.files


def download(file_id, dest):
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return os.path.getsize(dest)


def main():
    years = sys.argv[1:] or [str(y) for y in range(2024, datetime.date.today().year + 1)]
    folder = list_folder()
    for y in years:
        fid = folder.get(y)
        if not fid:
            raise RuntimeError(f"{y}: 文件夹里没找到，拒绝生成不完整快照")
        dest = os.path.join(HERE, f"oe_{y}.csv")
        if int(y) < datetime.date.today().year and os.path.isfile(dest):
            with open(dest, encoding="utf-8") as cached:
                if cached.read(80).startswith("gameid,"):
                    print(f"[cached] {y}: reuse complete historical CSV")
                    continue
        temporary = dest + ".tmp"
        size = download(fid, temporary)
        # 校验:必须是 CSV(以 gameid 开头),不能是 HTML 错误页
        with open(temporary, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
        ok = head.startswith("gameid,")
        print(f"[{'ok' if ok else 'BAD'}] {y}: {size/1e6:.1f} MB  -> {dest}")
        if not ok:
            os.unlink(temporary)
            if "Quota exceeded" in head or "Too many users have viewed or downloaded" in head:
                raise RuntimeError(f"{y}: Oracle's Elixir Google Drive download quota exceeded; cached CSV and ratings preserved, retry after upstream quota recovery")
            raise RuntimeError(f"{y}: 下载内容不是 CSV")
        os.replace(temporary, dest)


if __name__ == "__main__":
    main()
