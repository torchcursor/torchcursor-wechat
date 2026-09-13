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

console.log("\n[3] v1.5.0：单风格 + 无底纹 + 排版参数");
check("只剩卡片笔记一个风格", Object.keys(win.STYLES).length === 1 && !!win.STYLES.cardnote,
  Object.keys(win.STYLES).join(","));
check("正文颜色 80% 黑 #333333", stage.innerHTML.indexOf("color:#333333") > -1);
check("标题字重 700（不再 850 挤成一团）",
  stage.innerHTML.indexOf("font-weight:850") === -1 && stage.innerHTML.indexOf("font-weight:700") > -1);
check("重点标注 100% 黑", stage.innerHTML.indexOf("color:#000000") > -1);
check("每个块左右内边距 ≥15px（不贴边）", /padding:\d+px 15px \d+px 15px/.test(stage.innerHTML));
check("无底纹残留（无段落底线/分节边框）",
  stage.innerHTML.indexOf("border-bottom:1px solid #e6e3d8") === -1 &&
  stage.innerHTML.indexOf("border:1px solid #e6e3d8;border-radius:6px") === -1);

console.log("\n[5] 点色板换全文底色（双层包裹随粘贴保留）");
clickByValue("swatches", "#f2f6fb");
check("预览底色切成淡蓝 #f2f6fb", (stage.style.backgroundColor || "").indexOf("242, 246, 251") > -1,
  stage.style.backgroundColor);
check("粘贴内容里底色层换成淡蓝",
  stage.innerHTML.indexOf('<section style="background-color:#f2f6fb;padding:24px 16px;">') > -1);
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

console.log("\n[9] v1.4.0：单行分段 + 真实图片 + 头部图片链接");
$("md").value = "第一行内容\n第二行内容\n![配图](https://mmbiz.qpic.cn/x.jpg)\n![占位](说明文字)";
win.paint();
const ps = Array.from(stage.querySelectorAll("p")).map(p => p.textContent);
check("单换行即分段（两行各自成段，不再并成一大段）",
  ps.some(t => t.indexOf("第一行内容") > -1) && ps.some(t => t.indexOf("第二行内容") > -1) &&
  !ps.some(t => t.indexOf("第一行内容") > -1 && t.indexOf("第二行内容") > -1),
  JSON.stringify(ps.slice(0, 4)));
const bodyImg = stage.querySelector('img[src="https://mmbiz.qpic.cn/x.jpg"]');
check("正文真实图片：带 URL 的 ![描述](链接) 渲染为圆角 <img>",
  !!bodyImg && bodyImg.getAttribute("style").indexOf("border-radius:12px") > -1,
  bodyImg ? bodyImg.getAttribute("style") : "未找到 img");
check("无 URL 的 ![占位](说明) 仍是文字占位框",
  stage.innerHTML.indexOf("[ 图片：占位 ]") > -1 || stage.innerHTML.indexOf("占位") > -1);
$("cardImg").value = "https://mmbiz.qpic.cn/top.jpg";
$("cardImg").oninput();
check("头部图片链接：有 URL 渲染真图（圆角 + 细修饰边框）",
  stage.innerHTML.indexOf('border-radius:12px;border:1px solid') > -1,
  "headCard 区未找到圆角边框图片");
$("cardImg").value = "";
$("cardImg").oninput();
check("头部图片链接留空时回落圆角占位框",
  stage.innerHTML.indexOf("border-radius:12px;padding:26px 8px") > -1);

console.log("\n[10] 全程无脚本错误");
check("没有未捕获异常", errors.length === 0, errors.join("; "));

console.log("\n结果：" + pass + " 通过 / " + fail + " 失败");
process.exit(fail ? 1 : 0);
