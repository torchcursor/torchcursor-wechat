/* 控制台真机验证：用 jsdom 打开 studio.html，模拟点按钮，检查渲染结果是否真的变了。 */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const FILE = path.join(__dirname, "..", "studio.html");
const html = fs.readFileSync(FILE, "utf-8");

const errors = [];
const dom = new JSDOM(html, {
  runScripts: "dangerously",
  pretendToBeVisual: true,
  beforeParse(win) {
    win.addEventListener("error", e => errors.push("window.onerror: " + e.message));
    // jsdom 默认不带 canvas，控制台里对 canvas 取上下文要能优雅降级
    win.HTMLCanvasElement.prototype.getContext = function () { return null; };
    win.URL.createObjectURL = function () { return "blob:stub"; };
  }
});

const win = dom.window, doc = win.document;
const $ = id => doc.getElementById(id);
const stage = $("stage");

let pass = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { pass++; console.log("  ✓ " + name); }
  else { fail++; console.log("  ✗ " + name + (extra ? "  → " + extra : "")); }
}
function clickByText(containerId, text) {
  const btns = Array.from($(containerId).querySelectorAll("button"));
  const b = btns.find(x => x.textContent.trim() === text);
  if (!b) throw new Error("找不到按钮：" + text + "（" + containerId + " 里现有：" +
    btns.map(x => x.textContent.trim()).join(" / ") + "）");
  b.click();
  return b;
}
function clickByValue(containerId, value) {
  const b = $(containerId).querySelector('[data-value="' + value + '"]');
  if (!b) throw new Error("找不到 data-value=" + value + "（" + containerId + "）");
  b.click();
  return b;
}

console.log("控制台真机验证\n");

console.log("[1] 初始化");
check("脚本无运行时错误", errors.length === 0, errors.join("; "));
check("控制台 UI 按钮已生成", $("segStyle").querySelectorAll("button").length === 3);
check("底纹按钮 3 个", $("segBg").querySelectorAll("button").length === 3);
check("底色色板 7 个", $("swatches").querySelectorAll("button").length === 7);
check("预览区已渲染内容", stage.innerHTML.length > 500);

console.log("\n[2] 结构（1.2.0）：牺牲壳双层包裹 + 全文无表格");
check("全文底色双层包裹：外层牺牲壳 + 内层底色层（实测只丢最外层容器）",
  /^<section>\s*<section style="background-color:#/.test(stage.innerHTML.trim()),
  stage.innerHTML.trim().slice(0, 80));
check("预览容器有底色", (stage.style.backgroundColor || "").length > 0,
  stage.style.backgroundColor);
check("全文不再使用表格（微信会把表格转成带边框的表格组件）",
  (stage.innerHTML.match(/<table/g) || []).length === 0,
  "表格数=" + (stage.innerHTML.match(/<table/g) || []).length);
check("头部卡片左右分栏用 inline-block（不出边框，清洗后优雅退化）",
  stage.innerHTML.indexOf("display:inline-block;width:62%") > -1 &&
  stage.innerHTML.indexOf("display:inline-block;width:38%") > -1);
check("全文没有虚线边框（占位框会被当成小方框）",
  stage.innerHTML.indexOf("dashed") === -1);
check("编号分节标题为段落堆叠（编号+PART 同段）",
  stage.innerHTML.indexOf(">01&nbsp;<span") > -1);
check("正文有内容（段落/分节）", stage.innerHTML.indexOf("PART") > -1 && stage.innerHTML.indexOf("<p ") > -1);

console.log("\n[3] 点按钮切风格");
clickByText("segStyle", "熔炉橙");
check("切到熔炉橙后强调色变了", stage.innerHTML.indexOf("#c2410c") > -1);
check("熔炉橙不渲染头部卡片",
  stage.innerHTML.indexOf("border-radius:6px;background-color") === -1);
clickByText("segStyle", "卡片笔记");
check("切回卡片笔记后有头部卡片",
  stage.innerHTML.indexOf("border-radius:6px;background-color") > -1);

console.log("\n[4] 点按钮切底纹");
clickByText("segBg", "横线纸");
const ruled = (stage.innerHTML.match(/border-bottom:1px solid #e6e3d8/g) || []).length;
const ruledBg = (stage.innerHTML.match(/background-color:#fafaf4[^"]*border-bottom:1px solid #e6e3d8/g) || []).length;
check("横线纸：正文段落带细底线且每条线所在块都有底色（margin 已转 padding 防露白）",
  ruled >= 3 && ruledBg === ruled,
  "细线数=" + ruled + " 带底色=" + ruledBg);
clickByText("segBg", "方格纸");
check("方格纸：出现分节边框区块", stage.innerHTML.indexOf("border:1px solid #e6e3d8;border-radius:6px") > -1);
clickByText("segBg", "无底纹");
check("回到无底纹：正文无段落底线",
  (stage.innerHTML.match(/padding-bottom:12px;border-bottom/g) || []).length === 0);

console.log("\n[5] 点色板换全文底色（双层包裹随粘贴保留）");
clickByValue("swatches", "#f2f6fb");
check("预览底色切成淡蓝 #f2f6fb", (stage.style.backgroundColor || "").indexOf("242, 246, 251") > -1,
  stage.style.backgroundColor);
check("粘贴内容里底色层换成淡蓝",
  stage.innerHTML.indexOf('<section style="background-color:#f2f6fb;padding:28px 22px;">') > -1);
check("色板联动文字标签", $("pageBgLabel").textContent.indexOf("#f2f6fb") > -1,
  $("pageBgLabel").textContent);
clickByValue("swatches", "none");
check("选「无」回落到风格默认米白 #fafaf4",
  (stage.style.backgroundColor || "").indexOf("250, 250, 244") > -1,
  stage.style.backgroundColor);
check("选「无」后粘贴内容不包裹（白底直出）",
  !/^<section><section/.test(stage.innerHTML.trim()),
  stage.innerHTML.trim().slice(0, 80));
check("「无」有可见文字标签", Array.from($("swatches").querySelectorAll("button"))
  .some(b => b.textContent.trim() === "无"));

console.log("\n[6] 开关");
const before = (stage.innerHTML.match(/PART/g) || []).length;
clickByText("segToggles", "编号分节 ✓");
const after = (stage.innerHTML.match(/PART/g) || []).length;
check("关掉编号分节后 PART 消失", before > 0 && after === 0, before + " → " + after);
clickByText("segToggles", "编号分节 ✗");
check("再开回来 PART 恢复", (stage.innerHTML.match(/PART/g) || []).length === before);

console.log("\n[7] 改文稿后重渲染");
const ta = $("md");
ta.value = "# 测试标题\n\n第一段正文。\n\n> !这是一句金句\n\n## 分节一\n\n- 条目甲\n- 条目乙\n";
ta.dispatchEvent(new win.Event("input"));
check("新文稿已渲染", stage.innerHTML.indexOf("第一段正文") > -1);
check("金句卡生效", stage.innerHTML.indexOf("这是一句金句") > -1);
check("自动编号分节 01", stage.innerHTML.indexOf(">01&nbsp;<span") > -1);
check("列表渲染为 ul/li", stage.innerHTML.indexOf("<ul") > -1 && stage.innerHTML.indexOf("<li") > -1);
check("首个 H1 未进正文（防双标题）", stage.innerHTML.indexOf("<h1") === -1);

console.log("\n[8] 按钮不崩");
try { $("copyBtn").click(); check("复制按钮可点击（jsdom 无 execCommand，走降级提示）", $("status").textContent.length > 0); }
catch (e) { check("复制按钮可点击", false, e.message); }
try { $("selBtn").click(); check("仅选中按钮可点击", true); }
catch (e) { check("仅选中按钮可点击", false, e.message); }
try { $("loadSample").click(); check("载入示例按钮可点击", stage.innerHTML.indexOf("三点打破工厂对流量的幻觉") > -1); }
catch (e) { check("载入示例按钮可点击", false, e.message); }

console.log("\n[9] 全程无脚本错误");
check("没有未捕获异常", errors.length === 0, errors.join("; "));

console.log("\n结果：" + pass + " 通过 / " + fail + " 失败");
process.exit(fail ? 1 : 0);
