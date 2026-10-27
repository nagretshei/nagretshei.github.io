// events.html 的互動演出地圖：載入 images/world-map.svg 後，點城市看活動、縮放、拖曳。
// 城市的活動清單在這裡直接比對頁面上卡片的英文地點，所以加卡片不用重跑地圖程式。
(function () {
  var fig = document.querySelector(".world-map");
  if (!fig || !window.fetch) return;
  var img = fig.querySelector("img");
  if (!img) return;

  fetch(img.getAttribute("src"))
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
    .then(init)
    .catch(function () {}); // 讀不到就留著原本的靜態圖

  function lang() {
    return document.documentElement.getAttribute("data-lang") === "zh" ? "zh" : "en";
  }

  function text(el) {
    return el ? el.textContent.replace(/\s+/g, " ").trim() : "";
  }

  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // 把每張卡片整理成 {date, title, card}，依城市分組
  function collectEvents(cities) {
    var byCity = {};
    var patterns = cities.map(function (c) {
      return { name: c.getAttribute("data-en"), re: new RegExp("(^|[^A-Za-z])" + escapeRe(c.getAttribute("data-en")) + "([^A-Za-z]|$)") };
    });
    document.querySelectorAll(".year-group .card").forEach(function (card) {
      var metaEn = text(card.querySelector(".meta.lang-en"));
      if (!metaEn || /not presented/i.test(metaEn)) return;
      var metaZh = text(card.querySelector(".meta.lang-zh")) || metaEn;
      var h3 = card.querySelector("h3");
      var titleEn = text(h3 && (h3.querySelector(".lang-en") || h3));
      var titleZh = text(h3 && (h3.querySelector(".lang-zh") || h3));
      var cutEn = metaEn.lastIndexOf(" · ");
      var cutZh = metaZh.lastIndexOf(" · ");
      var place = cutEn >= 0 ? metaEn.slice(cutEn + 3) : metaEn;
      var ev = {
        en: (cutEn >= 0 ? metaEn.slice(0, cutEn) + " · " : "") + titleEn,
        zh: (cutZh >= 0 ? metaZh.slice(0, cutZh) + " · " : "") + titleZh,
        card: card
      };
      patterns.forEach(function (p) {
        if (p.re.test(place)) (byCity[p.name] = byCity[p.name] || []).push(ev);
      });
    });
    cities.forEach(function (c) {
      var extra = c.getAttribute("data-extra");
      if (!extra) return;
      JSON.parse(extra).forEach(function (pair) {
        (byCity[c.getAttribute("data-en")] = byCity[c.getAttribute("data-en")] || []).push({ en: pair[0], zh: pair[1] });
      });
    });
    return byCity;
  }

  function init(svgText) {
    var stage = document.createElement("div");
    stage.className = "world-map-stage";
    stage.innerHTML = svgText;
    var svg = stage.querySelector("svg");
    if (!svg) return;
    img.parentNode.replaceChild(stage, img);
    svg.removeAttribute("role");

    var base = svg.getAttribute("viewBox").split(/\s+/).map(Number);
    var W = base[2], H = base[3];
    var view = { x: 0, y: 0, w: W, h: H };
    var MIN_W = W / 40; // 最多放大 40 倍，台灣這種小地方才分得開
    var cities = Array.prototype.slice.call(svg.querySelectorAll(".city"));
    var byCity = collectEvents(cities);

    // 透明的大圓當點擊範圍，手機比較好點
    var hitLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    hitLayer.setAttribute("class", "city-hits");
    cities.forEach(function (c) {
      var h = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      h.setAttribute("cx", c.getAttribute("cx"));
      h.setAttribute("cy", c.getAttribute("cy"));
      h.setAttribute("tabindex", "0");
      h.setAttribute("role", "button");
      h.setAttribute("aria-label", c.getAttribute("data-en"));
      h._city = c;
      hitLayer.appendChild(h);
    });
    svg.appendChild(hitLayer);
    var hits = Array.prototype.slice.call(hitLayer.childNodes);

    var controls = document.createElement("div");
    controls.className = "world-map-controls";
    controls.innerHTML =
      '<button type="button" data-act="in" aria-label="Zoom in">+</button>' +
      '<button type="button" data-act="out" aria-label="Zoom out">−</button>' +
      '<button type="button" data-act="europe"><span class="lang-en">Europe</span><span class="lang-zh">歐洲</span></button>' +
      '<button type="button" data-act="reset" aria-label="Reset">⟲</button>';
    stage.appendChild(controls);

    var tip = document.createElement("div");
    tip.className = "world-map-tip";
    tip.hidden = true;
    stage.appendChild(tip);

    var label = document.createElement("div");
    label.className = "world-map-label";
    label.hidden = true;
    stage.appendChild(label);

    var active = null;

    function apply() {
      svg.setAttribute("viewBox", view.x + " " + view.y + " " + view.w + " " + view.h);
      var k = view.w / W;
      var r = 4.6 * Math.pow(k, 0.85);
      cities.forEach(function (c) { c.setAttribute("r", r.toFixed(2)); });
      hits.forEach(function (h) { h.setAttribute("r", Math.max(r * 2.2, 11 * k).toFixed(2)); });
      stage.classList.toggle("zoomed", k < 0.999);
      if (active) placeTip(active[0]);
    }

    function setView(x, y, w) {
      w = Math.max(MIN_W, Math.min(W, w));
      var h = w * H / W;
      view.w = w;
      view.h = h;
      view.x = Math.max(0, Math.min(W - w, x));
      view.y = Math.max(0, Math.min(H - h, y));
      apply();
    }

    // 以畫面上 (fx, fy)（0–1 比例）為中心縮放
    function zoomAt(factor, fx, fy) {
      var px = view.x + fx * view.w, py = view.y + fy * view.h;
      var w = Math.max(MIN_W, Math.min(W, view.w / factor));
      setView(px - fx * w, py - fy * (w * H / W), w);
    }

    function frac(clientX, clientY) {
      var b = svg.getBoundingClientRect();
      return [(clientX - b.left) / b.width, (clientY - b.top) / b.height];
    }

    function europe() {
      var names = ["Limerick", "Helsinki", "Limassol", "Foggia", "Paris"];
      var xs = [], ys = [];
      cities.forEach(function (c) {
        if (names.indexOf(c.getAttribute("data-en")) >= 0) {
          xs.push(+c.getAttribute("cx"));
          ys.push(+c.getAttribute("cy"));
        }
      });
      var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
      var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
      var w = Math.max(x1 - x0, (y1 - y0) * W / H) * 1.25;
      setView((x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - (w * H / W) / 2, w);
    }

    controls.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      var act = b.getAttribute("data-act");
      if (act === "in") zoomAt(1.6, 0.5, 0.5);
      else if (act === "out") zoomAt(1 / 1.6, 0.5, 0.5);
      else if (act === "europe") europe();
      else setView(0, 0, W);
    });

    // 觸控板雙指縮放（瀏覽器送 ctrl+wheel）或 Ctrl/⌘ + 滾輪才縮放；一般滾輪照常捲頁面
    svg.addEventListener("wheel", function (e) {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      var f = frac(e.clientX, e.clientY);
      zoomAt(Math.exp(-e.deltaY * 0.01), f[0], f[1]);
    }, { passive: false });

    svg.addEventListener("dblclick", function (e) {
      var f = frac(e.clientX, e.clientY);
      zoomAt(2, f[0], f[1]);
    });

    // 拖曳＋兩指縮放
    var pointers = {};
    var drag = null;
    var moved = false;

    svg.addEventListener("pointerdown", function (e) {
      lastPointer = e.pointerType || "mouse";
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      var ids = Object.keys(pointers);
      moved = false;
      if (ids.length === 1) {
        drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
      } else if (ids.length === 2) {
        var a = pointers[ids[0]], b = pointers[ids[1]];
        drag = { pinch: Math.hypot(a.x - b.x, a.y - b.y), w: view.w, vx: view.x, vy: view.y, mid: frac((a.x + b.x) / 2, (a.y + b.y) / 2) };
      }
    });

    svg.addEventListener("pointermove", function (e) {
      if (!pointers[e.pointerId] || !drag) return;
      pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
      var ids = Object.keys(pointers);
      var b = svg.getBoundingClientRect();
      if (ids.length >= 2 && drag.pinch) {
        var p = pointers[ids[0]], q = pointers[ids[1]];
        var d = Math.hypot(p.x - q.x, p.y - q.y);
        var w = Math.max(MIN_W, Math.min(W, drag.w * drag.pinch / d));
        var cx = drag.vx + drag.mid[0] * drag.w, cy = drag.vy + drag.mid[1] * (drag.w * H / W);
        setView(cx - drag.mid[0] * w, cy - drag.mid[1] * (w * H / W), w);
        moved = true;
      } else if (ids.length === 1 && !drag.pinch) {
        var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
        if (moved && view.w < W) {
          setView(drag.vx - dx * view.w / b.width, drag.vy - dy * view.h / b.height, view.w);
          svg.setPointerCapture && svg.setPointerCapture(e.pointerId);
        }
      }
    });

    function up(e) {
      delete pointers[e.pointerId];
      if (Object.keys(pointers).length === 0) drag = null;
    }
    svg.addEventListener("pointerup", up);
    svg.addEventListener("pointercancel", up);

    function placeTip(c) {
      // 手機上地圖太矮，卡片改放在地圖下方
      var below = stage.offsetWidth < 520;
      tip.classList.toggle("below", below);
      if (below) { tip.style.left = tip.style.top = ""; return; }
      var sb = stage.getBoundingClientRect();
      var cb = c.getBoundingClientRect();
      var x = cb.left + cb.width / 2 - sb.left;
      var y = cb.top - sb.top;
      tip.style.left = "0px";
      tip.style.top = "0px";
      var tw = tip.offsetWidth, th = tip.offsetHeight;
      var left = Math.max(4, Math.min(sb.width - tw - 4, x - tw / 2));
      var top = y - th - 10;
      if (top < 4) top = cb.bottom - sb.top + 10;
      tip.style.left = left + "px";
      tip.style.top = top + "px";
    }

    function openTip(list) {
      var L = lang();
      tip.innerHTML = "";
      var close = document.createElement("button");
      close.type = "button";
      close.className = "world-map-tip-close";
      close.setAttribute("aria-label", "Close");
      close.textContent = "×";
      close.addEventListener("click", closeTip);
      tip.appendChild(close);
      list.forEach(function (c) {
        var h = document.createElement("strong");
        h.textContent = c.getAttribute("data-" + L) + (L === "zh" ? "，" : ", ") + c.getAttribute("data-country-" + L);
        var ul = document.createElement("ul");
        (byCity[c.getAttribute("data-en")] || []).forEach(function (ev) {
          var li = document.createElement("li");
          if (ev.card) {
            var a = document.createElement("a");
            a.href = "#";
            a.textContent = ev[L];
            a.addEventListener("click", function (e) {
              e.preventDefault();
              ev.card.scrollIntoView({ behavior: "smooth", block: "center" });
              ev.card.classList.remove("flash");
              void ev.card.offsetWidth;
              ev.card.classList.add("flash");
            });
            li.appendChild(a);
          } else {
            li.textContent = ev[L];
          }
          ul.appendChild(li);
        });
        tip.appendChild(h);
        tip.appendChild(ul);
      });
      if (active) active.forEach(function (c) { c.classList.remove("active"); });
      active = list;
      list.forEach(function (c) { c.classList.add("active"); });
      tip.hidden = false;
      label.hidden = true;
      placeTip(list[0]);
    }

    function closeTip() {
      tip.hidden = true;
      if (active) active.forEach(function (c) { c.classList.remove("active"); });
      active = null;
    }

    // 城市很密時點擊範圍會重疊：螢幕上 6px 內的城市一起列出，不然就開最近的那個
    var lastPointer = "mouse";

    function citiesNear(clientX, clientY) {
      var b = svg.getBoundingClientRect();
      var f = frac(clientX, clientY);
      var px = view.x + f[0] * view.w, py = view.y + f[1] * view.h;
      var perPx = view.w / b.width;
      var scored = cities.map(function (c) {
        return { c: c, d: Math.hypot(c.getAttribute("cx") - px, c.getAttribute("cy") - py) / perPx };
      }).sort(function (a, z) { return a.d - z.d; });
      var reach = lastPointer === "touch" ? 14 : 6; // 手指比滑鼠不準，範圍放寬
      var near = scored.filter(function (x) { return x.d - scored[0].d < reach; }).map(function (x) { return x.c; });
      return { list: near.length ? near : [scored[0].c], perPx: perPx };
    }

    hitLayer.addEventListener("click", function (e) {
      if (moved || !e.target._city) return;
      var hit = citiesNear(e.clientX, e.clientY), near = hit.list;
      // 3 個以上擠在一起而且還能放大：以最近的城市為中心，放大到它和最近的鄰居分開約 24px，不跳長清單
      // （用城市座標不用點擊位置，手指幾 px 的誤差放大幾十倍會跑出畫面）
      if (near.length >= 3 && view.w > MIN_W + 1) {
        var c0 = near[0], gap = Infinity;
        near.slice(1).forEach(function (z) {
          gap = Math.min(gap, Math.hypot(c0.getAttribute("cx") - z.getAttribute("cx"), c0.getAttribute("cy") - z.getAttribute("cy")));
        });
        var w = Math.max(MIN_W, Math.min(W, view.w / Math.max(2.5, 24 * hit.perPx / Math.max(gap, 0.01))));
        closeTip();
        setView(c0.getAttribute("cx") - w / 2, c0.getAttribute("cy") - (w * H / W) / 2, w);
        return;
      }
      openTip(near);
    });
    hitLayer.addEventListener("keydown", function (e) {
      if ((e.key === "Enter" || e.key === " ") && e.target._city) {
        e.preventDefault();
        openTip([e.target._city]);
      }
    });
    svg.addEventListener("click", function (e) {
      if (!moved && !e.target._city) closeTip();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeTip();
    });
    var langBtn = document.querySelector(".lang-switch");
    if (langBtn) langBtn.addEventListener("click", function () { setTimeout(function () { if (active) openTip(active); }, 0); });

    // 滑鼠滑過：國家或城市顯示名稱
    svg.addEventListener("pointermove", function (e) {
      if (e.pointerType !== "mouse" || drag && moved) { label.hidden = true; return; }
      var t = e.target, L = lang(), s = "";
      if (t._city) {
        var f = frac(e.clientX, e.clientY);
        var px = view.x + f[0] * view.w, py = view.y + f[1] * view.h, bestD = Infinity;
        cities.forEach(function (c) {
          var d = Math.hypot(c.getAttribute("cx") - px, c.getAttribute("cy") - py);
          if (d < bestD) { bestD = d; s = c.getAttribute("data-" + L); }
        });
      }
      else if (t.classList && t.classList.contains("country")) s = t.getAttribute("data-" + L);
      if (!s) { label.hidden = true; return; }
      var sb = stage.getBoundingClientRect();
      label.textContent = s;
      label.hidden = false;
      label.style.left = Math.min(sb.width - label.offsetWidth - 4, e.clientX - sb.left + 12) + "px";
      label.style.top = (e.clientY - sb.top + 14) + "px";
    });
    svg.addEventListener("pointerleave", function () { label.hidden = true; });

    apply();
  }
})();
