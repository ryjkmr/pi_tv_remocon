# 起動
# nohup python3 app.py &
# http://ipアドレス:8080 でアクセス

from flask import Flask, render_template, request, redirect, jsonify
import subprocess
import requests
from datetime import datetime
import pytz

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


API_KEY = 'NHK番組表APIのKEY'
AREA = '130'
CHANNELS = {
    '総合': 'g1',
    'Eテレ': 'e1',
    'BS1': 's1'
}

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
    def format_time(t):
        dt = datetime.fromisoformat(t).astimezone(pytz.timezone('Asia/Tokyo'))
        return dt.strftime('%H:%M')

    results = []
    for name, sid in CHANNELS.items():
        url = f'https://api.nhk.or.jp/v2/pg/now/{AREA}/{sid}.json?key={API_KEY}'
        try:
            res = requests.get(url)
            data = res.json()
            program_data = data.get('nowonair_list', {}).get(sid, {})

            now = program_data.get('present')
            next_program = program_data.get('following')

            result = {"channel": name}

            if now:
                result["now"] = {
                    'title': now['title'],
                    'start': format_time(now['start_time']),
                    'end': format_time(now['end_time']),
                    'subtitle': now.get('subtitle', '(なし)')
                }

            if next_program:
                result["next"] = {
                    'title': next_program['title'],
                    'start': format_time(next_program['start_time']),
                    'end': format_time(next_program['end_time']),
                    'subtitle': next_program.get('subtitle', '(なし)')
                }

            results.append(result)

        except Exception:
            continue

    return jsonify(results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
    