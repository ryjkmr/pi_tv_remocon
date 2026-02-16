# NHK番組API V3対応版。2026.2.14


# 起動
# nohup python3 app.py &
# http://ipアドレス:8080 でアクセス

from flask import Flask, render_template, request, redirect, jsonify
import subprocess
import requests
from datetime import datetime
import pytz
import re

app = Flask(__name__)

DEFAULT_COLOR = "#555555"  # 色未指定のときのデフォルト色
REMOTE_NAME = "regza_z8000"

# ボタン定義（表示名, KEY, 色） ※色は省略可
BUTTONS = [
    ("電源", "KEY_POWER", "red"),
    ("BS", "KEY_BS", "blue"),
    ("地", "KEY_CHIDEJI", "#228B22"),  # forest green
    None,
    ("1", "KEY_1"),
    ("2", "KEY_2"),
    ("3", "KEY_3"),
    ("4", "KEY_4"),
    None,
    ("5", "KEY_5"),
    ("6", "KEY_6"),
    ("7", "KEY_7"),
    ("8", "KEY_8"),
    None,
    ("9", "KEY_9"),
    ("10", "KEY_10"),
    ("11", "KEY_11"),
    ("12", "KEY_12"),
    None,
    ("音量大", "KEY_VOLUMEUP", "orange"),
    ("音量小", "KEY_VOLUMEDOWN", "orange"),
    ("CH_UP", "KEY_CHANNELUP", "green"),
    ("CH_DWN", "KEY_CHANNELDOWN", "green"),
    None,
    ("MUTE", "KEY_MUTE", "#888888"),
]


API_KEY = '自分のAPIキーを入れる'
AREA = '130' #東京
CHANNELS = {
    '総合': 'g1',
    'Eテレ': 'e1',
    'BS1': 's1'
}


# NHK 番組表API Ver.3 (2026-01-13〜) のエンドポイント
# 参考: ポータルの「PgNowTv Ver.3」(Resource URL: https://program-api.nhk.jp/v3/papiPgNowTv ...)
NHK_NOW_TV_V3_URL = "https://program-api.nhk.jp/v3/papiPgNowTv"

@app.route("/")
def index():
    return render_template("index.html", buttons=BUTTONS, default_color=DEFAULT_COLOR)

@app.route("/send", methods=["POST"])
def send():
    key = request.form.get("key")
    if key:
        try:
            subprocess.run(["irsend", "SEND_ONCE", REMOTE_NAME, key], check=True)
        except subprocess.CalledProcessError:
            pass
    return redirect("/")

@app.route("/programs")
def programs():
    results = []
    JST = pytz.timezone("Asia/Tokyo")

    def parse_iso(ts: str) -> datetime:
        # "+0900" → "+09:00" のような表記揺れを吸収
        if isinstance(ts, str) and re.search(r"[+-]\d{4}$", ts):
            ts = ts[:-5] + ts[-5:-2] + ":" + ts[-2:]
        return datetime.fromisoformat(ts)

    def format_time(t: str) -> str:
        dt = parse_iso(t).astimezone(JST)
        return dt.strftime("%H:%M")

    def iter_program_objects(obj):
        """再帰的に走査し、開始/終了/タイトルっぽい要素を持つdictを列挙します（V3向け）"""
        if isinstance(obj, dict):
            keys = obj.keys()
            has_start = ("startDate" in keys) or ("start_time" in keys)
            has_end = ("endDate" in keys) or ("end_time" in keys)
            has_title = ("name" in keys) or ("title" in keys) or ("headline" in keys)
            if has_start and has_end and has_title:
                yield obj
            for v in obj.values():
                yield from iter_program_objects(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from iter_program_objects(v)

    def extract_present_following_v3(data, service_id: str):
        """
        PgNowTv V3レスポンス（例: {"g1": {...}}）から、
        .{service}.publication[] の startDate/endDate/name/description を使って
        現在/次の番組を返します。
        """
        if not isinstance(data, dict) or service_id not in data:
            return None

        root = data.get(service_id)
        if not isinstance(root, dict):
            return None

        # サービス名（UI表示用）※従来情報が残っている場合だけ使う。なければ service_id にフォールバック
        service_name = service_id
        pubmeta = root.get("publishedOn")
        if isinstance(pubmeta, list) and pubmeta and isinstance(pubmeta[0], dict):
            ig = pubmeta[0].get("identifierGroup")
            if isinstance(ig, dict):
                service_name = (
                    ig.get("shortenedDisplayName")
                    or ig.get("shortenedName")
                    or ig.get("broadcastDisplayName")
                    or service_name
                )
            service_name = service_name or pubmeta[0].get("name") or service_id

        pubs = root.get("publication")
        if not isinstance(pubs, list) or not pubs:
            return None

        candidates = []
        for o in pubs:
            if not isinstance(o, dict):
                continue

            start_ts = o.get("startDate")
            end_ts = o.get("endDate")
            title = o.get("name") or ""
            desc = o.get("description") or ""

            if not (isinstance(start_ts, str) and isinstance(end_ts, str) and title):
                continue

            try:
                sdt = parse_iso(start_ts).astimezone(JST)
                edt = parse_iso(end_ts).astimezone(JST)
            except Exception:
                continue

            candidates.append({
                "title": title,
                # 既存のUIキー subtitle を流用（中身は description）
                "subtitle": desc,
                "start_time": start_ts,
                "end_time": end_ts,
                "_sdt": sdt,
                "_edt": edt,
            })

        if not candidates:
            return None

        now_jst = datetime.now(JST)

        present = None
        following = None

        onair = [c for c in candidates if c["_sdt"] <= now_jst < c["_edt"]]
        if onair:
            present = sorted(onair, key=lambda c: c["_sdt"], reverse=True)[0]

        upcoming = [c for c in candidates if c["_sdt"] >= now_jst]
        if upcoming:
            following = sorted(upcoming, key=lambda c: c["_sdt"])[0]

        def strip(x):
            if not x:
                return None
            x = dict(x)
            x.pop("_sdt", None)
            x.pop("_edt", None)
            return x

        return {
            "service_name": service_name,
            "present": strip(present),
            "following": strip(following),
        }


    def fetch_nowonair(service_id: str):
        # Ver.3 のみ
        params_v3 = {"service": service_id, "area": AREA, "key": API_KEY}
        r = requests.get(NHK_NOW_TV_V3_URL, params=params_v3, timeout=5)
        r.raise_for_status()
        data = r.json()
        return extract_present_following_v3(data, service_id)

    for name, sid in CHANNELS.items():
        program_data = fetch_nowonair(sid)
        if not program_data:
            continue

        now = program_data.get("present")
        next_program = program_data.get("following")

        result = {"channel": name}

        if now:
            result["now"] = {
                "title": now.get("title", ""),
                "start": format_time(now["start_time"]),
                "end": format_time(now["end_time"]),
                "subtitle": now.get("subtitle", "(なし)"),
            }

        if next_program:
            result["next"] = {
                "title": next_program.get("title", ""),
                "start": format_time(next_program["start_time"]),
                "end": format_time(next_program["end_time"]),
                "subtitle": next_program.get("subtitle", "(なし)"),
            }

        results.append(result)

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
