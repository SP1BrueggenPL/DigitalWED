/* Obsługa kotłowni – kontrola dzienna elektryka (CD-00001499).
   Logika przeniesiona z prototypu; zapis i odczyt przez endpointy platformy. */
(function(){
"use strict";
var CFG = JSON.parse(document.getElementById("elektryk-config").textContent);
var LIMITS = CFG.limits;
var entries = CFG.entries, isEditor = !!CFG.isEditor;
function $(id){ return document.getElementById(id); }
function el(tag, attrs, kids){
  var e = document.createElement(tag);
  if (attrs) for (var k in attrs){
    if (k === "text") e.textContent = attrs[k];
    else if (k === "class") e.className = attrs[k];
    else if (k.slice(0,2) === "on") e.addEventListener(k.slice(2), attrs[k]);
    else if (attrs[k] !== null && attrs[k] !== undefined && attrs[k] !== false) e.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
  }
  (kids || []).forEach(function(c){ if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
  return e;
}
function parseNum(s){
  if (s === null || s === undefined) return NaN;
  s = String(s).trim().replace(/\s/g,"").replace(",",".");
  if (!/^-?\d+(\.\d+)?$/.test(s)) return NaN;
  return parseFloat(s);
}
function fmt(n){ return (typeof n === "number" && isFinite(n)) ? n.toLocaleString("pl-PL",{maximumFractionDigits:3}) : "–"; }
function pad(n){ return (n<10?"0":"")+n; }
function dDate(iso){ var d = new Date(iso); return isNaN(d) ? "–" : pad(d.getDate())+"."+pad(d.getMonth()+1)+"."+d.getFullYear(); }
function dTime(iso){ var d = new Date(iso); return isNaN(d) ? "–" : pad(d.getHours())+":"+pad(d.getMinutes()); }
function monthKey(iso){ var d = new Date(iso); return d.getFullYear()+"-"+pad(d.getMonth()+1); }
var MONTHS = ["styczeń","luty","marzec","kwiecień","maj","czerwiec","lipiec","sierpień","wrzesień","październik","listopad","grudzień"];
function toast(msg, isErr){ var t=$("toast"); t.textContent=msg; t.className = "alert app-toast " + (isErr ? "alert-error" : "alert-success"); t.hidden=false; clearTimeout(toast._t); toast._t=setTimeout(function(){t.hidden=true;},3500); }

/* register */
var selMonth = "all";
function cell(text, cls){ return el("td",{class:cls||"",text:text}); }
function okCell(val){ var td = el("td"); if (val === "Nie") td.appendChild(el("span",{class:"badge-count",text:"Nie"})); else if (val) td.appendChild(el("span",{class:"app-ok",text:val})); else td.textContent="–"; return td; }
function filtered(){ return selMonth==="all" ? entries : entries.filter(function(e){ return monthKey(e.d.start)===selMonth; }); }
function renderMonths(){
  var s = $("month"), keys = {};
  entries.forEach(function(e){ keys[monthKey(e.d.start)] = 1; });
  var list = Object.keys(keys).sort().reverse();
  s.textContent = "";
  s.appendChild(el("option",{value:"all",text:"Wszystkie miesiące"}));
  list.forEach(function(k){ var p=k.split("-"); s.appendChild(el("option",{value:k,text:MONTHS[parseInt(p[1],10)-1]+" "+p[0]})); });
  if (selMonth!=="all" && !keys[selMonth]) selMonth = "all";
  s.value = selMonth;
}
function renderStock(){
  var box = $("stock"); box.textContent = "";
  var lowCount = 0;
  if (entries.length){
    var d = entries[0].d;
    [["sol_mag","Sól zmiękczająca – magazyn","worki"],["p138_mag","Eurocept P138S – magazyn","l"],["d280_mag","Eurocept D280 – magazyn","l"]].forEach(function(x){
      var low = typeof d[x[0]]==="number" && d[x[0]] < LIMITS[x[0]];
      if (low) lowCount++;
      box.appendChild(el("div",{class:"process-card"+(low?" app-low-card":"")},[
        el("div",{class:"process-card-bar"}),
        el("div",{class:"process-card-body"},[
          el("div",{class:"process-card-num",text:x[1]}),
          el("div",{class:"process-card-title app-stock-val",text: fmt(d[x[0]]) + " " + x[2]}),
          el("div",{class:"process-card-desc",text: "Próg zamówienia: " + LIMITS[x[0]] + " " + x[2] + ", stan z " + dDate(d.start)})
        ]),
        el("div",{class:"process-card-footer"},[ el("span",{class:"status-chip " + (low ? "app-chip-low" : "status-chip--done"), text: low ? "Poniżej normy – zamów" : "W normie"}) ])
      ]));
    });
  }
  document.querySelectorAll("[data-lowbadge]").forEach(function(b){ b.textContent = String(lowCount); b.hidden = lowCount === 0; b.setAttribute("aria-label", lowCount + " poniżej normy"); });
}
function renderTable(){
  var tb = $("tbody"); tb.textContent = "";
  var rows = filtered();
  $("empty").hidden = rows.length > 0;
  $("count").hidden = !rows.length; $("count").textContent = String(rows.length);
  document.querySelectorAll(".adm-col").forEach(function(c){ c.hidden = !isEditor; });
  rows.forEach(function(e){
    var d = e.d, tr = el("tr");
    tr.appendChild(cell(dDate(d.start),"sticky"));
    tr.appendChild(cell(dTime(d.start)));
    tr.appendChild(cell(fmt(d.sol_duzy)));
    tr.appendChild(cell(fmt(d.sol_maly)));
    tr.appendChild(cell(fmt(d.sol_mag), d.sol_mag < LIMITS.sol_mag ? "app-cell-low" : ""));
    tr.appendChild(cell(fmt(d.p138_zb)));
    tr.appendChild(cell(fmt(d.p138_mag), d.p138_mag < LIMITS.p138_mag ? "app-cell-low" : ""));
    tr.appendChild(cell(fmt(d.d280_zb)));
    tr.appendChild(cell(fmt(d.d280_mag), d.d280_mag < LIMITS.d280_mag ? "app-cell-low" : ""));
    tr.appendChild(cell(d.zrzut === "Inna" ? "Inna: " + (d.zrzut_inna||"") : (d.zrzut||"–"), "wrap"));
    ["pompa1","pompa2","pompa3","pompa4","zawor1","zawor2"].forEach(function(k){
      var td = el("td",{},[ el("div",{style:"font-weight:700",text:d[k+"_n"]||"–"}) ]);
      tr.appendChild(td);
    });
    tr.appendChild(cell(fmt(d.cisnienie)));
    tr.appendChild(cell(fmt(d.licznik_schl)));
    tr.appendChild(cell(fmt(d.licznik_zm)));
    tr.appendChild(cell(d.kolumna||"–"));
    tr.appendChild(okCell(d.czystosc));
    tr.appendChild(cell(d.uwagi||"", "wrap"));
    if (isEditor){
      tr.appendChild(el("td",{},[ el("button",{type:"button",class:"app-del",text:"Usuń",onclick:function(){
        if (!confirm("Usunąć wpis z " + dDate(d.start) + ", " + dTime(d.start) + "? Tej operacji nie można cofnąć.")) return;
        fetch(CFG.deleteUrl.replace("/0/", "/" + e.id + "/"), { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value } })
          .then(function(r){ if (!r.ok) throw new Error(); entries = entries.filter(function(x){ return x.id !== e.id; }); renderRegister(); setStatus(); toast("Wpis usunięty"); })
          .catch(function(){ toast("Nie udało się usunąć wpisu.", true); });
      }}) ]));
    }
    tb.appendChild(tr);
  });
}
function renderRegister(){ renderMonths(); renderStock(); renderTable(); }

function csvEsc(x){ x = (x===undefined||x===null) ? "" : String(x); return /[;"\n\r]/.test(x) ? '"' + x.replace(/"/g,'""') + '"' : x; }
function num(x){ return (typeof x === "number" && isFinite(x)) ? String(x).replace(".",",") : ""; }
function exportCsv(){
  var rows = filtered();
  if (!rows.length){ toast("Brak wpisów do pobrania.", true); return; }
  var head = ["Data","Godzina","Sól – zbiornik duży [%]","Sól – zbiornik mały [%]","Sól – magazyn [worki]","Eurocept P138S – zbiornik [%]","Eurocept P138S – magazyn [l]","Eurocept D280 – zbiornik [%]","Eurocept D280 – magazyn [l]","Zrzut wody do kanału – przyczyna","Pompa 1 – nastawa","Pompa 2 – nastawa","Pompa 3 – nastawa","Pompa 4 – nastawa","Zawór 1 – nastawa","Zawór 2 – nastawa","Ciśnienie wody miejskiej [bar]","Stan licznika wody schładzacza","Stan licznika stacji zmiękczania wody","Nr pracującej kolumny","Czystość pomieszczenia","Uwagi"];
  var lines = [head.map(csvEsc).join(";")];
  rows.forEach(function(e){ var d = e.d; lines.push([dDate(d.start),dTime(d.start),num(d.sol_duzy),num(d.sol_maly),num(d.sol_mag),num(d.p138_zb),num(d.p138_mag),num(d.d280_zb),num(d.d280_mag),d.zrzut==="Inna"?"Inna: "+(d.zrzut_inna||""):d.zrzut,d.pompa1_n,d.pompa2_n,d.pompa3_n,d.pompa4_n,d.zawor1_n,d.zawor2_n,num(d.cisnienie),num(d.licznik_schl),num(d.licznik_zm),d.kolumna,d.czystosc,d.uwagi].map(csvEsc).join(";")); });
  var text = "\uFEFF" + lines.join("\r\n");
  var url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  var a = el("a", { href: url, download: "Obsluga_kotlowni_" + (selMonth==="all" ? "wszystkie" : selMonth) + ".csv" });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
}
function setStatus(){ $("reg-status").textContent = entries.length ? "Liczba wpisów: " + entries.length : ""; }

renderRegister();
setStatus();
$("month").addEventListener("change", function(){ selMonth = this.value; renderTable(); });
$("csv").addEventListener("click", exportCsv);
})();
