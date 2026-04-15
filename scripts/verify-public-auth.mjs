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
  if (new URL(page.url()).host !== authHost) {
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
    if (new URL(page.url()).host === expectedHost) {
      return;
    }
    await page.waitForTimeout(1500);
  }
  throw new Error(`Expected host ${expectedHost}, got ${page.url()}`);
}

async function screenshot(page, name) {
  await page.screenshot({ path: path.join(captureDir, `${name}.png`), fullPage: true });
}

async function verifyEdgeRoute(page, env, subdomain, screenshotName, expectedText = null) {
  const expectedHost = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await ensureHost(page, expectedHost, env);
  if (expectedText) {
    await page.waitForSelector(`text=${expectedText}`, { timeout: 30000 });
  }
  await screenshot(page, screenshotName);
}

async function verifyHeadlamp(page, env) {
  const expectedHost = `headlamp.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}/c/main`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.locator('text="Sign In"').first().waitFor({ state: "visible", timeout: 30000 });
  const popupPromise = page.waitForEvent("popup", { timeout: 30000 });
  await page.locator('text="Sign In"').first().click();
  const popup = await popupPromise;
  await popup.waitForLoadState("domcontentloaded");
  await maybeAutheliaLogin(popup, env);
  await popup.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  await popup.waitForTimeout(3000);
  const popupBody = await popup.textContent("body").catch(() => "");
  if (popup.url().includes("invalid_request") || popup.url().includes("invalid_client") || String(popupBody).includes("invalid_client")) {
    await screenshot(page, "headlamp-main-failed");
    await screenshot(popup, "headlamp-popup-failed");
    throw new Error(`Headlamp popup failed: ${popup.url()} :: ${String(popupBody).slice(0, 500)}`);
  }
  await page.waitForTimeout(3000);
  await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
  await ensureHost(page, expectedHost, env);
  const body = await page.textContent("body");
  if (String(body).includes("Authentication") && String(body).includes("Sign In")) {
    await screenshot(page, "headlamp-main-still-login");
    throw new Error("Headlamp remained on the internal login screen after OIDC callback");
  }
  await screenshot(page, "headlamp");
}

async function verifyNativeOidc(page, env, subdomain, screenshotName, options = {}) {
  const expectedHost = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}${options.pathSuffix || ""}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (options.preAuthAction) {
    await options.preAuthAction(page, env);
  }
  await ensureHost(page, expectedHost, env);
  if (options.expectSelector) {
    await page.waitForSelector(options.expectSelector, { timeout: 30000 });
  }
  await screenshot(page, screenshotName);
}

async function verifyAppNative(page, env, subdomain, screenshotName) {
  const expectedHost = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  const currentHost = new URL(page.url()).host;
  if (currentHost !== expectedHost) {
    throw new Error(`Expected app-native host ${expectedHost}, got ${page.url()}`);
  }
  if (currentHost === `auth.${env.DOMAIN_NAME}`) {
    throw new Error(`App-native route ${expectedHost} redirected to Authelia`);
  }
  await screenshot(page, screenshotName);
}

async function run() {
  const env = loadEnv(envPath);
  if (!env.AUTHELIA_ADMIN_PASSWORD) {
    throw new Error("AUTHELIA_ADMIN_PASSWORD is required in .env for browser auth verification");
  }
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await verifyEdgeRoute(page, env, "home", "homepage", "ChaosTest");
    await verifyEdgeRoute(page, env, "litmus", "litmus");
    await verifyEdgeRoute(page, env, "falco", "falco");
    await verifyEdgeRoute(page, env, "longhorn", "longhorn");
    await verifyHeadlamp(page, env);
    await verifyNativeOidc(page, env, "argocd", "argocd", { expectSelector: 'text="Applications"' });
    await verifyNativeOidc(page, env, "grafana", "grafana", {
      expectSelector: 'text="Home"',
      preAuthAction: async currentPage => {
        await maybeAutheliaLogin(currentPage, env);
      },
    });
    await verifyNativeOidc(page, env, "ansible", "semaphore", {
      expectSelector: 'text="Projects"',
      preAuthAction: async currentPage => {
        const oidcButton = currentPage.locator('text="Authelia"');
        if (await oidcButton.count()) {
          await oidcButton.first().click();
        }
      },
    });
    await verifyAppNative(page, env, "jellyfin", "jellyfin");
    await verifyAppNative(page, env, "radarr", "radarr");
    console.log(JSON.stringify({ result: "ok", captureDir }, null, 2));
  } finally {
    await context.close();
    await browser.close();
  }
}

run().catch(error => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
