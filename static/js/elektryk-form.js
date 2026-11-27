/* Obsługa kotłowni – kontrola dzienna elektryka (CD-00001499).
   Logika przeniesiona z prototypu; zapis i odczyt przez endpointy platformy. */
(function(){
"use strict";
var CFG = JSON.parse(document.getElementById("elektryk-config").textContent);
var LIMITS = CFG.limits;
var NAMES = {
  sol_mag: { prod: "Sól zmiękczająca", unit: "worków" },
  p138_mag: { prod: "Eurocept P138S", unit: "l" },
  d280_mag: { prod: "Eurocept D280", unit: "l" }
};
var STEPS = [
  { title: "Rozpoczęcie kontroli", help: "Data i godzina zapisują się automatycznie w chwili otwarcia formularza.", fields: [{ key: "start", type: "auto" }] },
  { title: "Sól zmiękczająca", help: "Wpisz stany po dosypaniu soli.", fields: [
    { key: "sol_duzy", type: "percent", label: "Poziom w zbiorniku dużym po dosypaniu" },
    { key: "sol_maly", type: "percent", label: "Poziom w zbiorniku małym po dosypaniu" },
    { key: "sol_mag", type: "number", label: "Stan na magazynie po dosypaniu", unit: "worki", unitLong: "worków", int: true, limit: LIMITS.sol_mag }
  ]},
  { title: "Eurocept P138S", help: "Wpisz stany po dolaniu środka.", fields: [
    { key: "p138_zb", type: "percent", label: "Poziom w zbiorniku po dolaniu" },
    { key: "p138_mag", type: "number", label: "Ilość na magazynie po dolaniu", unit: "l", unitLong: "l", limit: LIMITS.p138_mag }
  ]},
  { title: "Eurocept D280", help: "Wpisz stany po dolaniu środka.", fields: [
    { key: "d280_zb", type: "percent", label: "Poziom w zbiorniku po dolaniu" },
    { key: "d280_mag", type: "number", label: "Ilość na magazynie po dolaniu", unit: "l", unitLong: "l", limit: LIMITS.d280_mag }
  ]},
  { title: "Kontrola zrzutu wody do kanału", help: "Podaj przyczynę zrzutu.", fields: [{ key: "zrzut", type: "reason" }] },
  { title: "Kolektor C.O.", help: "Sprawdź i skoryguj nastawy zaworów i pomp na kolektorze C.O.", fields: [{ key: "co", type: "okgroup", items: [
    ["pompa1","Pompa 1"],["pompa2","Pompa 2"],["pompa3","Pompa 3"],["pompa4","Pompa 4"],["zawor1","Zawór 1"],["zawor2","Zawór 2"]
  ]}]},
  { title: "Ciśnienie wody miejskiej", help: "", fields: [{ key: "cisnienie", type: "number", label: "Ciśnienie", unit: "bar", max: 20 }] },
  { title: "Stan licznika wody schładzacza", help: "", fields: [{ key: "licznik_schl", type: "number", label: "Odczyt licznika", unit: "" }] },
  { title: "Stan licznika stacji zmiękczania wody", help: "", fields: [{ key: "licznik_zm", type: "number", label: "Odczyt licznika", unit: "" }] },
  { title: "Nr pracującej kolumny", help: "", fields: [{ key: "kolumna", type: "pick", label: "Która kolumna pracuje?", options: ["1","2"] }] },
  { title: "Czystość pomieszczenia", help: "", fields: [
    { key: "czystosc", type: "okone", label: "Pomieszczenie czyste" },
    { key: "uwagi", type: "text", label: "Uwagi (opcjonalnie)", sub: "Bez nazwisk i danych osobowych.", requiredIf: ["czystosc","Nie"] }
  ]},
  { title: "Sprawdź i wyślij", help: "Upewnij się, że wszystko się zgadza. Każdą sekcję możesz poprawić.", summary: true }
];
var REASONS = ["Odsalanie","Kondensat","Inna"];

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

var state = { step: 0, v: {}, raw: {}, saving: false, done: null };
var dbReady = true;

function newEntry(){
  state.step = 0; state.v = { start: new Date().toISOString() }; state.raw = {}; state.done = null; state.saving = false;
  renderWizard();
}

/* validation */
function validateField(f){
  var v = state.v, r = state.raw;
  if (f.type === "auto") return "";
  if (f.type === "percent" || f.type === "number"){
    var raw = r[f.key];
    if (raw === undefined || String(raw).trim() === "") return "Wpisz wartość.";
    var n = parseNum(raw);
    if (isNaN(n)) return "Wpisz liczbę (np. 45 lub 2,5).";
    if (n < 0) return "Wartość nie może być ujemna.";
    if (f.type === "percent" && n > 100) return "Podaj wartość od 0 do 100 %.";
    if (f.int && Math.round(n) !== n) return "Podaj liczbę całkowitą worków.";
    if (f.max !== undefined && n > f.max) return "Wartość wydaje się za duża – sprawdź odczyt.";
    v[f.key] = n; return "";
  }
  if (f.type === "reason"){
    if (!v.zrzut) return "Wybierz przyczynę.";
    if (v.zrzut === "Inna" && !(v.zrzut_inna||"").trim()) return "Opisz przyczynę.";
    return "";
  }
  if (f.type === "okgroup"){
    for (var i=0;i<f.items.length;i++){
      if (!(v[f.items[i][0]+"_n"]||"").trim()) return "Wpisz wartość nastawy przy każdej pozycji (brakuje: " + f.items[i][1] + ").";
    }
    return "";
  }
  if (f.type === "okone" || f.type === "pick"){ return v[f.key] ? "" : "Wybierz jedną z opcji."; }
  if (f.type === "text" && f.requiredIf && v[f.requiredIf[0]] === f.requiredIf[1] && !(v[f.key]||"").trim()) return "Opisz, co jest nie tak z czystością pomieszczenia.";
  return "";
}
function validateStep(i){
  var ok = true;
  (STEPS[i].fields||[]).forEach(function(f){
    var msg = validateField(f);
    var e = document.querySelector('[data-err="'+f.key+'"]');
    if (e) e.textContent = msg;
    var inp = $("f_"+f.key);
    if (inp) inp.classList.toggle("is-invalid", !!msg);
    if (msg) ok = false;
  });
  return ok;
}
function validateStepSilent(i){ var ok = true; (STEPS[i].fields||[]).forEach(function(f){ if (validateField(f)) ok = false; }); return ok; }
function lowItems(v){
  var out = [];
  ["sol_mag","p138_mag","d280_mag"].forEach(function(k){ if (typeof v[k] === "number" && v[k] < LIMITS[k]) out.push(k); });
  return out;
}

/* fields */
function choiceBtn(label, pressed, onClick, isNo){
  return el("button", { type:"button", class:"btn app-choice " + (pressed ? "btn-primary" : "btn-secondary") + (isNo ? " is-no" : ""), "aria-pressed": pressed?"true":"false", onclick:onClick, text:label });
}
function renderField(f){
  var v = state.v, r = state.raw;
  if (f.type === "auto"){
    var d = new Date(v.start);
    var dn = d.toLocaleDateString("pl-PL",{weekday:"long", day:"numeric", month:"long", year:"numeric"});
    return el("div",{class:"detail-field app-field"},[
      el("div",{class:"detail-label",text:"Rozpoczęto wpisywanie"}),
      el("div",{class:"app-bigtime",text:dTime(v.start)}),
      el("div",{class:"detail-value",text:dn.charAt(0).toUpperCase()+dn.slice(1)+" ("+dDate(v.start)+")"})
    ]);
  }
  if (f.type === "percent" || f.type === "number"){
    var id = "f_"+f.key;
    var input = el("input",{ id:id, class:"form-control app-big", type:"text", inputmode:"decimal", autocomplete:"off", enterkeyhint:"next" });
    input.value = r[f.key]!==undefined ? r[f.key] : "";
    var errEl = el("div",{class:"app-err","data-err":f.key});
    var note = f.limit !== undefined ? el("div",{class:"alert alert-error",hidden:true}) : null;
    var fill = null;
    function upd(){
      r[f.key] = input.value;
      var n = parseNum(input.value);
      if (fill) fill.style.height = (isNaN(n)?0:Math.max(0,Math.min(100,n)))+"%";
      if (note){
        if (!isNaN(n) && n < f.limit){
          note.hidden = false; note.textContent = "";
          note.appendChild(el("b",{text:"Poniżej progu " + f.limit + " " + f.unitLong + "."}));
          note.appendChild(document.createTextNode(" Po wysłaniu formularza zgłoszenie trafi e-mailem do odbiorców powiadomień."));
        } else note.hidden = true;
      }
      errEl.textContent = ""; input.classList.remove("is-invalid");
    }
    input.addEventListener("input", upd);
    input.addEventListener("keydown", function(e){ if (e.key === "Enter"){ e.preventDefault(); focusNextOrGo(input); } });
    var row = [el("div",{class:"app-numwrap"},[input, el("span",{class:"app-unit",text: f.type==="percent" ? "%" : (f.unit||"")})])];
    if (f.type === "percent"){
      fill = el("div",{class:"app-tank-fill"});
      row.unshift(el("div",{class:"app-tank","aria-hidden":"true"},[fill, el("div",{class:"app-tank-ticks"})]));
    }
    var lr = el("div",{class:"app-labelrow"},[ el("label",{for:id,text:f.label}) ]);
    if (f.limit !== undefined) lr.appendChild(el("span",{class:"badge badge-gold",text:"próg: " + f.limit + " " + f.unitLong}));
    setTimeout(upd,0);
    return el("div",{class:"form-group app-field"},[ lr, el("div",{class:"app-inrow"},row), errEl, note ]);
  }
  if (f.type === "reason"){
    var other = el("input",{ class:"form-control app-text app-other", type:"text", placeholder:"Opisz przyczynę…", "aria-label":"Inna przyczyna" });
    other.value = v.zrzut_inna||"";
    other.addEventListener("input", function(){ v.zrzut_inna = other.value; });
    var grid = el("div",{class:"app-choices", role:"group", "aria-label":"Przyczyna zrzutu"});
    var err = el("div",{class:"app-err","data-err":f.key});
    function draw(){
      grid.textContent = "";
      REASONS.forEach(function(rr){
        grid.appendChild(choiceBtn(rr, v.zrzut===rr, function(){ v.zrzut = rr; err.textContent=""; draw(); if (rr==="Inna") setTimeout(function(){ other.focus(); },0); }));
      });
      other.hidden = v.zrzut !== "Inna";
    }
    draw();
    return el("div",{class:"form-group app-field"},[ el("label",{text:"Przyczyna zrzutu"}), grid, other, err ]);
  }
  if (f.type === "okgroup"){
    var tb = el("tbody");
    f.items.forEach(function(it){
      var k = it[0];
      var nin = el("input",{ id:"f_"+k+"_n", class:"form-control", type:"text", maxlength:"30", autocomplete:"off", placeholder:"Wartość nastawy", "aria-label":"Wartość nastawy – " + it[1] });
      nin.value = v[k+"_n"]||"";
      nin.addEventListener("input", function(){ v[k+"_n"] = nin.value; nin.classList.remove("is-invalid"); var er=document.querySelector('[data-err="co"]'); if (er) er.textContent=""; });
      tb.appendChild(el("tr",{},[ el("td",{class:"row-label",text:it[1]}), el("td",{},[ el("div",{class:"app-nast"},[nin]) ]) ]));
    });
    var tbl = el("table",{class:"gas-table"},[ el("thead",{},[ el("tr",{},[ el("th",{text:"Element"}), el("th",{text:"Wartość nastawy"}) ]) ]), tb ]);
    return el("div",{class:"form-group app-field"},[ tbl, el("div",{class:"app-err","data-err":f.key}) ]);
  }
  if (f.type === "okone" || f.type === "pick"){
    var opts = f.type === "okone" ? [["OK",false],["Nie",true]] : f.options.map(function(o){ return [o,false]; });
    var ch2 = el("div",{class:"app-choices two", role:"group", "aria-label":f.label});
    function d2(){ ch2.textContent=""; opts.forEach(function(o){ ch2.appendChild(choiceBtn(f.type==="pick"?"Kolumna "+o[0]:o[0], v[f.key]===o[0], function(){ v[f.key]=o[0]; if (f.key==="czystosc"){ renderWizard(); var t=$("f_uwagi"); if (o[0]==="Nie" && t) t.focus(); } else d2(); }, o[1])); }); }
    d2();
    return el("div",{class:"form-group app-field"},[ el("label",{text:f.label}), ch2, el("div",{class:"app-err","data-err":f.key}) ]);
  }
  if (f.type === "text"){
    var req = f.requiredIf && v[f.requiredIf[0]] === f.requiredIf[1];
    var ta = el("textarea",{ class:"form-control app-text", id:"f_"+f.key, maxlength:"500" });
    ta.value = v[f.key]||"";
    var terr = el("div",{class:"app-err","data-err":f.key});
    ta.addEventListener("input", function(){ v[f.key] = ta.value; terr.textContent=""; ta.classList.remove("is-invalid"); });
    if (req) ta.setAttribute("placeholder","Co wymaga posprzątania lub zgłoszenia?");
    return el("div",{class:"form-group app-field"},[
      el("label",{for:"f_"+f.key,text: req ? "Uwagi (wymagane, bo zaznaczono „Nie”)" : f.label}),
      el("p",{class:"app-hint",text:f.sub||""}), ta, terr
    ]);
  }
}
function focusNextOrGo(input){
  var inputs = Array.prototype.slice.call(document.querySelectorAll("#wiz input[inputmode=decimal]"));
  var i = inputs.indexOf(input);
  if (i >= 0 && i < inputs.length-1) inputs[i+1].focus(); else goNext();
}

/* wizard */
function goNext(){
  if (!validateStep(state.step)) { var e = document.querySelector("#wiz .app-err:not(:empty)"); if (e) e.scrollIntoView({block:"center",behavior:"smooth"}); return; }
  state.step = Math.min(state.step+1, STEPS.length-1); renderWizard(true);
}
function goBack(){ state.step = Math.max(0, state.step-1); renderWizard(true); }

function pageHeader(title, sub){
  return el("div",{class:"page-header"},[ el("div",{class:"page-header-left"},[ el("h1",{text:title, tabindex:"-1", id:"step-title"}), el("div",{class:"doc-number",text:sub}) ]) ]);
}
function renderWizard(focus){
  var w = $("wiz"); w.textContent = "";
  if (state.done){ renderDone(w); return; }
  var s = STEPS[state.step], total = STEPS.length, pct = Math.round((state.step)/(total-1)*100);
  w.appendChild(pageHeader("Kontrola dzienna kotłowni", "Formularz CD-00001499, do uzupełnienia przez elektryka"));
  w.appendChild(el("div",{class:"etap-bar", role:"progressbar", "aria-valuemin":"1", "aria-valuemax":String(total), "aria-valuenow":String(state.step+1), "aria-label":"Postęp formularza"},[
    el("div",{class:"etap-step"},[ el("div",{class:"etap-dot",text:String(state.step+1)}), el("div",{class:"etap-label",text:"Krok"}) ]),
    el("div",{class:"etap-line", style:"background:linear-gradient(90deg,var(--brand-success) "+pct+"%,var(--brand-border) "+pct+"%)"}),
    el("div",{class:"etap-count",text:(state.step+1)+" z "+total})
  ]));
  var body = el("div",{class:"card-body"});
  if (s.help) body.appendChild(el("p",{class:"app-help",text:s.help}));
  if (s.summary) renderSummary(body);
  else (s.fields||[]).forEach(function(f){ body.appendChild(renderField(f)); });
  var head = el("div",{class:"card-header"},[ el("h3",{text:s.title}) ]);
  if (!s.summary) head.appendChild(el("span",{class:"section-id",text:"Pkt "+(state.step+1)}));
  w.appendChild(el("div",{class:"card"},[ head, body ]));

  var nav = el("div",{class:"app-nav"});
  if (state.step > 0) nav.appendChild(el("button",{type:"button",class:"btn btn-secondary",text:"Wstecz",onclick:goBack}));
  if (s.summary){
    var b = el("button",{type:"button",class:"btn btn-primary",text: state.saving ? "Wysyłanie…" : "Wyślij formularz", onclick:submit});
    if (state.saving || !dbReady) b.disabled = true;
    nav.appendChild(b);
  } else nav.appendChild(el("button",{type:"button",class:"btn btn-primary",text: state.step===0 ? "Rozpocznij" : "Dalej", onclick:goNext}));
  w.appendChild(nav);
  if (focus){
    window.scrollTo(0,0);
    var first = w.querySelector("input[inputmode=decimal]");
    if (first && window.matchMedia("(pointer:fine)").matches) first.focus(); else { var t=$("step-title"); if (t) t.focus({preventScroll:true}); }
  }
}

function dField(label, val, low){ return el("div",{class:"detail-field"},[ el("div",{class:"detail-label",text:label}), el("div",{class:"detail-value"+(low?" app-low":""),text:val}) ]); }
function renderSummary(box){
  var v = state.v;
  function sec(title, stepIdx, fields){
    box.appendChild(el("div",{class:"app-sum-sec"},[
      el("div",{class:"app-sum-head"},[ el("div",{class:"subsection-label",text:title}), el("button",{type:"button",class:"btn btn-secondary btn-sm",text:"Popraw",onclick:function(){ state.step = stepIdx; renderWizard(true); }}) ]),
      el("div",{class:"detail-grid"},fields)
    ]));
  }
  sec("Rozpoczęcie", 0, [ dField("Data i godzina", dDate(v.start)+", "+dTime(v.start)) ]);
  sec("Sól zmiękczająca", 1, [ dField("Zbiornik duży", fmt(v.sol_duzy)+" %"), dField("Zbiornik mały", fmt(v.sol_maly)+" %"), dField("Magazyn", fmt(v.sol_mag)+" worków", v.sol_mag < LIMITS.sol_mag) ]);
  sec("Eurocept P138S", 2, [ dField("Zbiornik", fmt(v.p138_zb)+" %"), dField("Magazyn", fmt(v.p138_mag)+" l", v.p138_mag < LIMITS.p138_mag) ]);
  sec("Eurocept D280", 3, [ dField("Zbiornik", fmt(v.d280_zb)+" %"), dField("Magazyn", fmt(v.d280_mag)+" l", v.d280_mag < LIMITS.d280_mag) ]);
  sec("Zrzut wody do kanału", 4, [ dField("Przyczyna", v.zrzut==="Inna" ? "Inna: "+(v.zrzut_inna||"") : v.zrzut) ]);
  sec("Kolektor C.O.", 5, STEPS[5].fields[0].items.map(function(it){ return dField(it[1], (v[it[0]+"_n"]||"").trim()); }));
  sec("Pomiary", 6, [ dField("Ciśnienie wody miejskiej", fmt(v.cisnienie)+" bar"), dField("Licznik wody schładzacza", fmt(v.licznik_schl)), dField("Licznik stacji zmiękczania", fmt(v.licznik_zm)), dField("Pracująca kolumna", v.kolumna) ]);
  sec("Czystość pomieszczenia", 10, [ dField("Czystość", v.czystosc, v.czystosc==="Nie"), dField("Uwagi", (v.uwagi||"").trim() || "–") ]);
}

function buildDoc(){
  var v = state.v, d = {
    start: v.start,
    sol_duzy: v.sol_duzy, sol_maly: v.sol_maly, sol_mag: v.sol_mag,
    p138_zb: v.p138_zb, p138_mag: v.p138_mag, d280_zb: v.d280_zb, d280_mag: v.d280_mag,
    zrzut: v.zrzut, zrzut_inna: v.zrzut === "Inna" ? (v.zrzut_inna||"").trim().slice(0,200) : "",
    pompa1_n: (v.pompa1_n||"").trim(), pompa2_n: (v.pompa2_n||"").trim(), pompa3_n: (v.pompa3_n||"").trim(), pompa4_n: (v.pompa4_n||"").trim(), zawor1_n: (v.zawor1_n||"").trim(), zawor2_n: (v.zawor2_n||"").trim(),
    cisnienie: v.cisnienie, licznik_schl: v.licznik_schl, licznik_zm: v.licznik_zm,
    kolumna: v.kolumna, czystosc: v.czystosc, uwagi: (v.uwagi||"").trim().slice(0,500)
  };
  d.niski_stan = lowItems(d);
  return d;
}
async function submit(){
  if (state.saving) return;
  for (var i=0;i<STEPS.length-1;i++){ if (!validateStepSilent(i)){ state.step = i; renderWizard(true); validateStep(i); return; } }
  state.saving = true; renderWizard();
  var data = buildDoc();
  try {
    var resp = await fetch(CFG.submitUrl, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value },
      body: JSON.stringify(data)
    });
    var out = null;
    try { out = await resp.json(); } catch(e){ out = null; }
    state.saving = false;
    if (resp.ok && out && out.ok){ data.mailSent = !!out.mailSent; state.done = data; renderWizard(true); return; }
    renderWizard();
    toast(out && out.error ? out.error :
          (resp.status === 403 || resp.redirected) ? "Sesja wygasła lub brak uprawnień. Zaloguj się ponownie." :
          "Nie udało się wysłać. Sprawdź połączenie i spróbuj ponownie.", true);
  } catch(e){
    state.saving = false; renderWizard();
    toast("Nie udało się wysłać. Sprawdź połączenie i spróbuj ponownie.", true);
  }
}
function renderDone(w){
  var d = state.done;
  w.appendChild(pageHeader("Kontrola dzienna kotłowni", "Formularz CD-00001499, do uzupełnienia przez elektryka"));
  w.appendChild(el("div",{class:"alert alert-success"},[ el("div",{class:"app-done-title",text:"✓ Formularz wysłany"}), document.createTextNode("Wpis z " + dDate(d.start) + ", " + dTime(d.start) + " jest już w rejestrze.") ]));
  (d.niski_stan || []).forEach(function(k){
    var n = NAMES[k];
    var a = el("div",{class:"alert alert-error"},[ el("b",{text: n.prod + ": " + fmt(d[k]) + " " + n.unit + " na magazynie."}), document.createTextNode(" To poniżej progu " + LIMITS[k] + " " + n.unit + ".") ]);
    a.appendChild(el("div",{style:"margin-top:6px;font-size:12.5px",text: d.mailSent ? "Zgłoszenie zostało wysłane e-mailem do odbiorców powiadomień." : "Powiadomienie e-mail nie zostało wysłane – przekaż informację telefonicznie lub osobiście."}));
    w.appendChild(a);
  });
  w.appendChild(el("div",{class:"app-nav"},[
    el("a",{href:CFG.rejestrUrl,class:"btn btn-secondary",text:"Zobacz rejestr"}),
    el("button",{type:"button",class:"btn btn-primary",text:"Nowy wpis",onclick:newEntry})
  ]));
}

newEntry();
})();
