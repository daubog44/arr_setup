import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const repoRoot = process.cwd();
const envPath = path.join(repoRoot, ".env");
const captureDir = path.join(repoRoot, ".tmp", "playwright-captures");
fs.mkdirSync(captureDir, { recursive: true });
const valuesOutputPath = path.join(repoRoot, "k8s", "charts", "haac-stack", "values.yaml");
const valuesTemplatePath = path.join(
  repoRoot,
  "k8s",
  "charts",
  "haac-stack",
  "config-templates",
  "values.yaml.template",
);

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

function renderEnvPlaceholders(content, env) {
  return content.replace(/\$\{([A-Z0-9_]+)\}/g, (_, key) => env[key] ?? "");
}

function loadCatalogContent(env) {
  if (fs.existsSync(valuesOutputPath)) {
    return fs.readFileSync(valuesOutputPath, "utf8");
  }
  return renderEnvPlaceholders(fs.readFileSync(valuesTemplatePath, "utf8"), env);
}

function loadIngressCatalog(content, domainName) {
  const lines = content.split(/\r?\n/);
  let inIngresses = false;
  let currentName = "";
  let current = {};
  const endpoints = [];

  const flush = () => {
    if (!currentName || !current.subdomain || !current.auth_strategy) {
      currentName = "";
      current = {};
      return;
    }
    const enabled = !["0", "false", "no", "off"].includes(String(current.enabled ?? "true").toLowerCase());
    if (enabled) {
      endpoints.push({
        name: currentName,
        subdomain: current.subdomain,
        namespace: current.namespace || "",
        service: current.service || "",
        auth: current.auth_strategy,
        url: `https://${current.subdomain}.${domainName}`,
      });
    }
    currentName = "";
    current = {};
  };

  for (const rawLine of lines) {
    const stripped = rawLine.trim();
    if (!inIngresses) {
      if (stripped === "ingresses:") {
        inIngresses = true;
      }
      continue;
    }
    if (/^\S/.test(rawLine)) {
      break;
    }
    if (!stripped || stripped.startsWith("#")) {
      continue;
    }
    const entryMatch = rawLine.match(/^  ([A-Za-z0-9_-]+):\s*$/);
    if (entryMatch) {
      flush();
      currentName = entryMatch[1];
      current = {};
      continue;
    }
    const propMatch = rawLine.match(/^    ([A-Za-z0-9_]+):\s*(.*)$/);
    if (propMatch && currentName) {
      const [, key, value] = propMatch;
      const cleaned = value.trim().replace(/^['"]|['"]$/g, "");
      if (cleaned) {
        current[key] = cleaned;
      }
    }
  }

  flush();
  return endpoints;
}

const routeChecks = {
  homepage: {
    expectedText: "/Benvenuto nel Nucleo Autogenerativo|Management|Media|Security/",
    unexpectedText: "ChaosTest",
  },
  headlamp: { type: "headlamp" },
  ntfy: {},
  litmus: {
    appNativeSelector: 'text=/Welcome to Litmus|Sign In|Username|Password/',
    async login(currentPage, env) {
      const username = currentPage.locator('input[name="username"], input[placeholder="Username"]').first();
      const password = currentPage.locator('input[name="password"], input[placeholder="Password"]').first();
      const submit = currentPage.locator('button:has-text("Sign In"), button[type="submit"]').first();
      if (!(await username.count()) || !(await password.count()) || !(await submit.count())) {
        return;
      }
      await username.fill(env.LITMUS_ADMIN_USERNAME || "admin");
      await password.fill(env.LITMUS_ADMIN_PASSWORD || env.AUTHELIA_ADMIN_PASSWORD);
      await submit.click();
    },
    async waitForSuccess(currentPage) {
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await currentPage.waitForTimeout(1000);
        const body = String((await currentPage.textContent("body").catch(() => "")) || "");
        const url = currentPage.url();
        if (body.includes("invalid credentials") || body.includes("Invalid Credentials") || body.includes("Login failed")) {
          throw new Error(`Litmus login failed: ${body}`);
        }
        if (!url.includes("/login") && /Chaos|Workflow|Probe|Targets|Project/i.test(body)) {
          const manualBootstrapMarkers = [
            "Deploying your Infrastructure",
            "kubectl apply -f",
            "There are no Kubernetes Chaos Infrastructures",
            "Enable Chaos in Environments",
          ];
          for (const marker of manualBootstrapMarkers) {
            if (body.includes(marker)) {
              throw new Error(`Litmus still requires manual bootstrap: ${marker}`);
            }
          }
          const environmentsLink = currentPage.locator('text=/Environments/i').first();
          if (await environmentsLink.count()) {
            await environmentsLink.click().catch(() => {});
            await currentPage.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
            const environmentBody = String((await currentPage.textContent("body").catch(() => "")) || "");
            for (const marker of manualBootstrapMarkers) {
              if (environmentBody.includes(marker)) {
                throw new Error(`Litmus environment page still requires manual bootstrap: ${marker}`);
              }
            }
          }
          return;
        }
      }
      throw new Error(`Litmus did not reach an authenticated landing page: ${currentPage.url()}`);
    },
  },
  falco: {},
  longhorn: {},
  jellyfin: { appNativeSelector: 'text=/Jellyfin|Sign In|Username|Password/' },
  radarr: { appNativeSelector: 'text=/Radarr|Login|Username|Password/' },
  sonarr: { appNativeSelector: 'text=/Sonarr|Login|Username|Password/' },
  prowlarr: { appNativeSelector: 'text=/Prowlarr|Login|Username|Password/' },
  autobrr: { appNativeSelector: 'text=/autobrr|Login|Username|Password/i' },
  qbittorrent: { appNativeSelector: 'text=/qBittorrent|Username|Password|Web UI/' },
  argocd: {
    type: "native_oidc",
    async preAuthAction(currentPage) {
      const oidcButton = currentPage.locator('text="Log in via Authelia"');
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if (await oidcButton.count()) {
          await oidcButton.first().waitFor({ state: "visible", timeout: 30000 });
          await oidcButton.first().click();
          return;
        }
        await currentPage.waitForTimeout(1000);
      }
      throw new Error("ArgoCD OIDC login button did not appear");
    },
    async waitForSuccess(currentPage, env) {
      for (let attempt = 0; attempt < 20; attempt += 1) {
        await currentPage.waitForTimeout(1000);
        const currentUrl = currentPage.url();
        const parsed = new URL(currentUrl);
        if (
          parsed.host === `argocd.${env.DOMAIN_NAME}` &&
          !parsed.pathname.startsWith("/auth/callback")
        ) {
          break;
        }
        const body = await currentPage.textContent("body").catch(() => "");
        if (String(body).includes("failed to get token")) {
          throw new Error(`ArgoCD callback failed: ${body}`);
        }
      }
      await currentPage.waitForSelector('text=/Applications|New App|Settings/', { timeout: 30000 });
    },
  },
  grafana: {
    type: "native_oidc",
    async preAuthAction() {},
    async waitForSuccess(currentPage, env) {
      for (let attempt = 0; attempt < 30; attempt += 1) {
        await currentPage.waitForTimeout(1000);
        const body = String((await currentPage.textContent("body").catch(() => "")) || "");
        const currentUrl = new URL(currentPage.url());
        if (body.includes("Failed to get token from provider") || body.includes("Login failed")) {
          throw new Error(`Grafana OIDC callback failed: ${body}`);
        }
        if (
          currentUrl.host === `grafana.${env.DOMAIN_NAME}` &&
          !currentUrl.pathname.startsWith("/login") &&
          (body.includes("Dashboards") || body.includes("Explore") || body.includes("Connections") || body.includes("Administration"))
        ) {
          await verifyGrafanaObservability(currentPage);
          return;
        }
      }
      throw new Error(`Grafana did not reach an authenticated landing page: ${currentPage.url()}`);
    },
  },
  semaphore: {
    type: "native_oidc",
    async preAuthAction(currentPage) {
      const oidcButton = currentPage.locator('text="Authelia"');
      for (let attempt = 0; attempt < 20; attempt += 1) {
        if (await oidcButton.count()) {
          await oidcButton.first().waitFor({ state: "visible", timeout: 30000 });
          await oidcButton.first().click();
          return;
        }
        await currentPage.waitForTimeout(1000);
      }
      throw new Error("Semaphore Authelia button did not appear");
    },
    async waitForSuccess(currentPage) {
      await currentPage.waitForSelector('text=/Projects|Task Templates|Dashboard|New Project|Create Demo Project/', {
        timeout: 30000,
      });
    },
  },
};

async function maybeAutheliaLogin(page, env) {
  const authHost = `auth.${env.DOMAIN_NAME}`;
  for (let step = 0; step < 4; step += 1) {
    await page.waitForLoadState("domcontentloaded");
    if (new URL(page.url()).host !== authHost) {
      return;
    }
    const username = page.locator('#username-textfield, input[autocomplete="username"]').first();
    const password = page.locator('#password-textfield, input[autocomplete="current-password"]').first();
    const signIn = page.locator('#sign-in-button, button[type="submit"], input[type="submit"]').first();
    const consentButton = page.locator('#openid-consent-accept').first();
    for (let attempt = 0; attempt < 30; attempt += 1) {
      if ((await username.count()) || (await consentButton.count())) {
        break;
      }
      await page.waitForTimeout(500);
    }
    if (await username.count()) {
      await username.waitFor({ state: "visible", timeout: 30000 });
      const usernameEnabled = await username.isEnabled().catch(() => false);
      if (usernameEnabled) {
        const currentUsername = await username.inputValue().catch(() => "");
        if (currentUsername !== "admin") {
          await username.fill("admin");
        }
      }
      await password.waitFor({ state: "visible", timeout: 30000 });
      const passwordEnabled = await password.isEnabled().catch(() => false);
      if (!passwordEnabled) {
        await page.waitForTimeout(1000);
        continue;
      }
      await password.fill(env.AUTHELIA_ADMIN_PASSWORD);
      await signIn.waitFor({ state: "visible", timeout: 30000 });
      const signInEnabled = await signIn.isEnabled().catch(() => false);
      if (!signInEnabled) {
        await page.waitForTimeout(1000);
        continue;
      }
      await signIn.click();
      await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
      continue;
    }
    if (await consentButton.count()) {
      await consentButton.waitFor({ state: "visible", timeout: 30000 });
      await consentButton.click();
      await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
      continue;
    }
    await page.waitForTimeout(1000);
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

async function fetchJson(page, relativePath) {
  const response = await page.evaluate(async (targetPath) => {
    const result = await fetch(targetPath, { credentials: "same-origin" });
    return {
      status: result.status,
      text: await result.text(),
    };
  }, relativePath);
  if (response.status < 200 || response.status >= 300) {
    throw new Error(`Request to ${relativePath} failed with status ${response.status}: ${response.text}`);
  }
  try {
    return JSON.parse(response.text);
  } catch {
    throw new Error(`Request to ${relativePath} did not return JSON: ${response.text}`);
  }
}

const GRAFANA_API_SERVER_DASHBOARD_UID = "09ec8aa1e996d6ffcd6817bbaff4db1b";
const GRAFANA_PROMETHEUS_DATASOURCE_UID = "prometheus";

function prometheusScalar(result) {
  const scalar = result?.data?.result?.[0]?.value?.[1];
  const numeric = Number(scalar);
  if (!Number.isFinite(numeric)) {
    throw new Error(`Prometheus query did not return a scalar value: ${JSON.stringify(result)}`);
  }
  return numeric;
}

async function queryGrafanaPrometheus(page, query) {
  return fetchJson(
    page,
    `/api/datasources/proxy/uid/${GRAFANA_PROMETHEUS_DATASOURCE_UID}/api/v1/query?query=${encodeURIComponent(query)}`,
  );
}

async function verifyGrafanaObservability(page) {
  const grafanaHost = new URL(page.url()).host;
  await page.goto(
    `https://${grafanaHost}/d/${GRAFANA_API_SERVER_DASHBOARD_UID}/kubernetes-api-server?orgId=1&from=now-1h&to=now&timezone=utc`,
    {
    waitUntil: "domcontentloaded",
    timeout: 60000,
    },
  );
  await page.waitForSelector('text=/Kubernetes\\s*\\/\\s*API server/i', { timeout: 30000 });
  await page.waitForTimeout(8000);

  const apiserverTargetCount = await queryGrafanaPrometheus(page, 'count(up{job="apiserver"})');
  if (prometheusScalar(apiserverTargetCount) < 1) {
    throw new Error(
      `Grafana reached the dashboard, but Prometheus exposed no apiserver targets: ${JSON.stringify(apiserverTargetCount)}`,
    );
  }

  const clusterCount = await queryGrafanaPrometheus(page, 'count(count by (cluster) (up{job="apiserver",cluster!=""}))');
  if (prometheusScalar(clusterCount) < 1) {
    throw new Error(
      `Grafana reached the dashboard, but the official cluster selector resolved no values for job="apiserver": ${JSON.stringify(clusterCount)}`,
    );
  }

  const instanceCount = await queryGrafanaPrometheus(
    page,
    'count(count by (instance) (up{job="apiserver",cluster!="",instance!=""}))',
  );
  if (prometheusScalar(instanceCount) < 1) {
    throw new Error(
      `Grafana reached the dashboard, but the official instance selector resolved no values for job="apiserver": ${JSON.stringify(instanceCount)}`,
    );
  }

  const bodyText = await page.locator("body").innerText();
  if (/Unable to find datasource|Datasource not found/i.test(bodyText)) {
    throw new Error("Grafana rendered the API server dashboard, but the Prometheus datasource is still missing.");
  }
  if (/No data/i.test(bodyText)) {
    throw new Error("Grafana rendered the API server dashboard, but one or more panels still report 'No data'.");
  }
}

async function verifyHomepageWidgets(page) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const bodyText = await page.locator("body").innerText();
    if (!bodyText.includes("Grafana") || !bodyText.includes("qBittorrent")) {
      await page.waitForTimeout(1000);
      continue;
    }
    if (/HTTP status 500/i.test(bodyText) || /API Error Information/i.test(bodyText)) {
      if (attempt === 29) {
        if (/HTTP status 500/i.test(bodyText)) {
          throw new Error("Homepage still rendered an operator widget with HTTP status 500.");
        }
        throw new Error("Homepage still rendered widget API errors for one or more official service cards.");
      }
      await page.waitForTimeout(1000);
      continue;
    }
    return;
  }
  throw new Error("Homepage did not render the expected Grafana and qBittorrent cards before widget verification.");
}

async function verifyEdgeRoute(page, env, subdomain, screenshotName, expectedText = null, unexpectedText = null) {
  const expectedHost = `${subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await ensureHost(page, expectedHost, env);
  const routeErrorMarkers = ["Bad gateway", "502", "Application is not available", "Internal Server Error", "404 page not found"];
  const body = String((await page.textContent("body").catch(() => "")) || "");
  for (const marker of routeErrorMarkers) {
    if (body.includes(marker)) {
      await screenshot(page, `${screenshotName}-gateway-error`);
      throw new Error(`${screenshotName} rendered a route-level failure after auth: ${marker}`);
    }
  }
  if (expectedText) {
    await page.waitForSelector(`text=${expectedText}`, { timeout: 30000 });
  }
  if (unexpectedText) {
    const refreshedBody = String((await page.textContent("body").catch(() => "")) || "");
    if (refreshedBody.includes(unexpectedText)) {
      throw new Error(`${screenshotName} rendered unexpected text: ${unexpectedText}`);
    }
  }
  if (subdomain === "home") {
    await verifyHomepageWidgets(page);
  }
  await screenshot(page, screenshotName);
}

async function verifyHeadlamp(page, env) {
  const expectedHost = `headlamp.${env.DOMAIN_NAME}`;
  await verifyEdgeRoute(page, env, "headlamp", "headlamp");
  await ensureHost(page, expectedHost, env);
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  const routeErrorMarkers = ["Bad gateway", "502", "Application is not available", "Internal Server Error", "404 page not found"];
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await page.waitForTimeout(1000);
    const body = String((await page.textContent("body").catch(() => "")) || "");
    const url = page.url();
    for (const marker of routeErrorMarkers) {
      if (body.includes(marker)) {
        await screenshot(page, "headlamp-main-gateway-error");
        throw new Error(`Headlamp rendered a route-level failure after edge auth: ${marker}`);
      }
    }
    if (body.includes("Unauthorized")) {
      await screenshot(page, "headlamp-main-unauthorized");
      throw new Error("Headlamp rendered an unauthorized cluster state behind edge auth");
    }
    if (
      (body.includes("All Clusters") || body.includes("Projects")) &&
      (body.includes("in-cluster") || body.includes("main"))
    ) {
      await screenshot(page, "headlamp-main");
      return;
    }
    if (!url.includes("/login") && body.includes("Headlamp") && !body.includes("Use A Token")) {
      await screenshot(page, "headlamp-main");
      return;
    }
  }
  await screenshot(page, "headlamp-main-still-login");
  const body = String((await page.textContent("body").catch(() => "")) || "");
  if (body.includes("Use A Token")) {
    throw new Error("Headlamp still presented the internal token login behind edge auth");
  }
  throw new Error(`Headlamp did not reach an authenticated cluster landing page: ${page.url()}`);
}

async function verifyNativeOidc(page, env, endpoint, screenshotName, options = {}) {
  const expectedHost = `${endpoint.subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}${options.pathSuffix || ""}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (options.preAuthAction) {
    await options.preAuthAction(page, env, endpoint);
  }
  await ensureHost(page, expectedHost, env);
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  if (options.waitForSuccess) {
    await options.waitForSuccess(page, env, endpoint);
  }
  await screenshot(page, screenshotName);
}

async function verifyAppNative(page, env, endpoint, screenshotName, options = {}) {
  const expectedHost = `${endpoint.subdomain}.${env.DOMAIN_NAME}`;
  await page.goto(`https://${expectedHost}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  const currentHost = new URL(page.url()).host;
  if (currentHost !== expectedHost) {
    throw new Error(`Expected app-native host ${expectedHost}, got ${page.url()}`);
  }
  if (currentHost === `auth.${env.DOMAIN_NAME}`) {
    throw new Error(`App-native route ${expectedHost} redirected to Authelia`);
  }
  const body = String((await page.textContent("body").catch(() => "")) || "");
  for (const marker of ["404 page not found", "Bad Gateway", "502", "Application is not available", "Internal Server Error"]) {
    if (body.includes(marker)) {
      throw new Error(`App-native route ${expectedHost} rendered an error page: ${marker}`);
    }
  }
  if (options.appNativeSelector) {
    await page.waitForSelector(options.appNativeSelector, { timeout: 30000 });
  } else if (!body.trim()) {
    throw new Error(`App-native route ${expectedHost} rendered an empty body`);
  }
  if (options.login) {
    await options.login(page, env, endpoint);
  }
  if (options.waitForSuccess) {
    await options.waitForSuccess(page, env, endpoint);
  }
  await screenshot(page, screenshotName);
}

async function run() {
  const env = loadEnv(envPath);
  if (!env.AUTHELIA_ADMIN_PASSWORD) {
    throw new Error("AUTHELIA_ADMIN_PASSWORD is required in .env for browser auth verification");
  }
  env.LITMUS_ADMIN_USERNAME = env.LITMUS_ADMIN_USERNAME || "admin";
  env.LITMUS_ADMIN_PASSWORD = env.LITMUS_ADMIN_PASSWORD || env.AUTHELIA_ADMIN_PASSWORD;
  const ingressCatalog = loadIngressCatalog(loadCatalogContent(env), env.DOMAIN_NAME);
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    for (const endpoint of ingressCatalog.filter(endpoint => endpoint.auth === "edge_forward_auth")) {
      const routeConfig = routeChecks[endpoint.name] || {};
      if (routeConfig.type === "headlamp") {
        await verifyHeadlamp(page, env);
        continue;
      }
      await verifyEdgeRoute(
        page,
        env,
        endpoint.subdomain,
        endpoint.name,
        routeConfig.expectedText ?? null,
        routeConfig.unexpectedText ?? null,
      );
    }
    for (const endpoint of ingressCatalog.filter(endpoint => endpoint.auth === "native_oidc")) {
      const routeConfig = routeChecks[endpoint.name];
      if (!routeConfig) {
        throw new Error(`No browser verification contract defined for native_oidc route ${endpoint.name}`);
      }
      await verifyNativeOidc(page, env, endpoint, endpoint.name, routeConfig);
    }
    for (const endpoint of ingressCatalog.filter(endpoint => endpoint.auth === "app_native")) {
      const routeConfig = routeChecks[endpoint.name] || {};
      await verifyAppNative(page, env, endpoint, endpoint.name, routeConfig);
    }
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
