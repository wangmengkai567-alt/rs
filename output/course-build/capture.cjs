const assert = require("node:assert/strict");
const { chromium } = require("C:/Users/Dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
(async () => {
  const browser = await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe", headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:930},deviceScaleFactor:3});
    await page.goto("http://127.0.0.1:8000/", {waitUntil:"domcontentloaded"});
    await page.waitForFunction(() => document.querySelector("#checkin-count").textContent === "6,442,127");
    await page.locator('[name=mode][value=region]').check();
    await page.locator("#bbox").fill("-97.81,30.22,-97.74,30.30");
    await page.locator("#start").fill("2010-10-19T23:55:27Z");
    await page.locator("#end").fill("2010-10-19T23:55:28Z");
    await page.locator("#submit").click();
    await page.waitForFunction(() => document.querySelector("#rows td")?.textContent === "1");
    await page.waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length >= 6);
    const row = await page.locator("#rows tr").first().locator("td").allTextContents();
    assert.ok(row.includes("22847"));
    await page.screenshot({path:"output/course-build/demo.png"});
    console.log("Captured live Austin query at 4320 x 2790");
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
