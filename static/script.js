function fetchPrograms() {
  fetch("/programs")
    .then(res => res.json())
    .then(data => {
      const list = document.getElementById("program-list");
      list.innerHTML = "";

      data.forEach(p => {
        const div = document.createElement("div");
        div.className = "program-item";

        const header = document.createElement("div");
        header.className = "program-channel";
        header.textContent = `📺 ${p.channel}`;
        div.appendChild(header);

        if (p.now) {
          const nowTitle = document.createElement("div");
          nowTitle.className = "program-title";
          nowTitle.textContent = `▶️ ${p.now.title} (${p.now.start}〜${p.now.end})`;
          div.appendChild(nowTitle);

          const nowSub = document.createElement("div");
          nowSub.className = "program-subtitle";
          nowSub.textContent = p.now.subtitle;
          nowSub.onclick = () => {
            nowSub.classList.toggle("expanded");
          };
          div.appendChild(nowSub);
        }

        if (p.next) {
          const br = document.createElement("br");  // 改行を入れる
          div.appendChild(br);

          const nextTitle = document.createElement("div");
          nextTitle.className = "program-title next";
          nextTitle.textContent = `⏭ 次: ${p.next.title} (${p.next.start}〜${p.next.end})`;
          div.appendChild(nextTitle);

          const nextSub = document.createElement("div");
          nextSub.className = "program-subtitle";
          nextSub.textContent = p.next.subtitle;
          nextSub.onclick = () => {
            nextSub.classList.toggle("expanded");
          };
          div.appendChild(nextSub);
        }


        list.appendChild(div);
      });
    });
}

// リモコン操作ボタン送信用（POST送信をfetchで）
function setupControlButtons() {
    const buttons = document.querySelectorAll(".control-button");
    buttons.forEach(btn => {
        btn.addEventListener("click", () => {
            const key = btn.dataset.key;
            fetch("/send", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: `key=${encodeURIComponent(key)}`
            });
        });
    });
}


fetchPrograms();
setupControlButtons();
setInterval(fetchPrograms, 20 * 60 * 1000); // 20分ごとに更新
