const assert = require("node:assert/strict");
const { copyFile } = require("node:fs/promises");
const { chromium } = require("C:/Users/Dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
(async () => {
  const browser = await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe", headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:930},deviceScaleFactor:3});
    await page.goto("http://127.0.0.1:8000/", {waitUntil:"domcontentloaded"});
    await page.waitForFunction(() => document.querySelector("#checkin-count").textContent === "6,442,127");
    await page.locator('[name=mode][value=region]').check();
    await page.locator("#bbox").fill("-97.81,30.22,-97.74,30.30");
    await page.locator("#submit").click();
    await page.waitForFunction(() => document.querySelectorAll("#rows tr").length === 200);
    await page.waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length >= 6);
    const blue = await page.locator(".checkin-point.shard1").count();
    const orange = await page.locator(".checkin-point.shard2").count();
    assert.ok(blue > 0 && orange > 0 && blue + orange === 200);
    await page.screenshot({path:"output/course-build/demo.png"});
    await copyFile("output/course-build/demo.png", "output/preview.png");
    console.log(`Captured Austin results with ${blue} shard1 points and ${orange} shard2 points`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
