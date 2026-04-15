import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const repoRoot = process.cwd();
const envPath = path.join(repoRoot, ".env");
const captureDir = path.join(repoRoot, ".tmp", "playwright-captures");
fs.mkdirSync(captureDir, { recursive: true });

function loadEnv(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const env = {};
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const [key, ...rest] = rawLine.split("=");
    let value = rest.join("=").trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    env[key.trim()] = value;
  }
  return env;
}

async function maybeAutheliaLogin(page, env) {
  const authHost = `auth.${env.DOMAIN_NAME}`;
  await page.waitForLoadState("domcontentloaded");
  const currentHost = new URL(page.url()).host;
  if (currentHost !== authHost) {
    return;
  }
  const username = page.locator('#username-textfield, input[autocomplete="username"]').first();
  const password = page.locator('#password-textfield, input[autocomplete="current-password"]').first();
  const signIn = page.locator('#sign-in-button, button[type="submit"], input[type="submit"]').first();
  const consentButton = page.locator('#openid-consent-accept').first();
  if (await username.count()) {
    await username.waitFor({ state: "visible", timeout: 30000 });
    await username.fill("admin");
    await password.fill(env.AUTHELIA_ADMIN_PASSWORD);
    await signIn.click();
    await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  }
  if (await consentButton.count()) {
    await consentButton.waitFor({ state: "visible", timeout: 15000 }).catch(() => {});
    await consentButton.click();
    await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  }
}

async function ensureHost(page, expectedHost, env) {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    await maybeAutheliaLogin(page, env);
    await page.waitForLoadState("domcontentloaded");
    const host = new URL(page.url()).host;
    if (host === expectedHost) {
      return;
    }
    await page.waitForTimeout(1500);
  }
  throw new Error(`Expected host ${expectedHost}, got ${page.url()}`);
}

async function waitForVisibleText(page, text, timeout = 30000) {
  await page.waitForSelector(`text=${text}`, { timeout });
}

async function completeAutheliaPopup(page, env) {
  await maybeAutheliaLogin(page, env);
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const currentHost = new URL(page.url()).host;
    if (currentHost !== `auth.${env.DOMAIN_NAME}`) {
      return;
    }
    await maybeAutheliaLogin(page, env);
    await page.waitForTimeout(1000);
  }
}

async function verifyEdgeRoute(page, env, subdomain, screenshotName, expectedText = null) {
  const expectedHost = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await ensureHost(page, expectedHost, env);
  if (expectedText) {
    await page.waitForSelector(`text=${expectedText}`, { timeout: 30000 });
  }
  await page.screenshot({ path: path.join(captureDir, `${screenshotName}.png`), fullPage: true });
}

async function verifyNativeOidc(page, env, subdomain, screenshotName, pathSuffix = "", expectSelector = null, postAuthAction = null) {
  const expectedHost = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}${pathSuffix}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await maybeAutheliaLogin(page, env);
  if (postAuthAction) {
    await postAuthAction(page);
  }
  await ensureHost(page, expectedHost, env);
  if (expectSelector) {
    await page.waitForSelector(expectSelector, { timeout: 30000 });
  }
  await page.screenshot({ path: path.join(captureDir, `${screenshotName}.png`), fullPage: true });
}

async function verifyHeadlamp(page, env) {
  const expectedHost = `headlamp.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}/c/main`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await waitForVisibleText(page, '"Sign In"');
  const popupPromise = page.waitForEvent("popup", { timeout: 30000 });
  await page.locator('text="Sign In"').first().click();
  const popup = await popupPromise;
  await popup.waitForLoadState("domcontentloaded");
  await completeAutheliaPopup(popup, env);
  await popup.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  await popup.waitForTimeout(5000);
  const popupUrl = popup.url();
  if (popupUrl.includes("invalid_request") || popupUrl.includes("invalid_client")) {
    throw new Error(`Headlamp popup failed: ${popupUrl}`);
  }
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await ensureHost(page, expectedHost, env);
  await waitForVisibleText(page, '"Headlamp"');
  await page.screenshot({ path: path.join(captureDir, "headlamp.png"), fullPage: true });
}

async function verifyAppNative(page, env, subdomain, screenshotName, expectedHost = null) {
  const host = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${host}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  const currentHost = new URL(page.url()).host;
  if (currentHost !== (expectedHost || host)) {
    throw new Error(`Expected app-native host ${expectedHost || host}, got ${page.url()}`);
  }
  if (currentHost === `auth.${env.DOMAIN_NAME}`) {
    throw new Error(`App-native route ${host} redirected to Authelia`);
  }
  await page.screenshot({ path: path.join(captureDir, `${screenshotName}.png`), fullPage: true });
}

async function run() {
  const env = loadEnv(envPath);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await verifyEdgeRoute(page, env, "home", "homepage", "ChaosTest");
    await verifyEdgeRoute(page, env, "litmus", "litmus");
    await verifyEdgeRoute(page, env, "falco", "falco");
    await verifyEdgeRoute(page, env, "longhorn", "longhorn");

    await verifyHeadlamp(page, env);
    await verifyNativeOidc(page, env, "argocd", "argocd", "", 'text="Applications"');
    await verifyNativeOidc(page, env, "grafana", "grafana", "", 'text="Home"', async (currentPage) => {
      if (new URL(currentPage.url()).host === `auth.${env.DOMAIN_NAME}`) {
        await maybeAutheliaLogin(currentPage, env);
      }
    });
    await verifyNativeOidc(page, env, "ansible", "semaphore", "", 'text="Projects"', async (currentPage) => {
      const currentHost = new URL(currentPage.url()).host;
      if (currentHost === `ansible.${env.DOMAIN_NAME}`) {
        const oidcButton = currentPage.locator('text="Authelia"');
        if (await oidcButton.count()) {
          await oidcButton.first().click();
        }
      }
    });

    await verifyAppNative(page, env, "jellyfin", "jellyfin");
    await verifyAppNative(page, env, "radarr", "radarr");

    console.log(JSON.stringify({ result: "ok", captures: captureDir }, null, 2));
  } finally {
    await context.close();
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
