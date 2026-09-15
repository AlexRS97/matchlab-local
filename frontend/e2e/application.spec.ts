import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
const scenario = JSON.parse(
  readFileSync(
    new URL("../../.runtime/ui-scenario.json", import.meta.url),
    "utf8",
  ),
);

test("real application loads every main page without browser errors", async ({
  page,
}) => {
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  for (const [path, title] of [
    ["/", "Hoy"],
    ["/learning", "Model lab"],
    ["/settings", "Settings"],
    ["/performance", "Performance"],
    ["/corners", "Córners"],
    ["/odds", "Comparador de cuotas"],
  ]) {
    await page.goto(path);
    await expect(
      page.getByRole("heading", { name: new RegExp(title) }).first(),
    ).toBeVisible();
    // Automatic training may be active; wait for page data, not every activity icon.
    await expect(
      page.getByText("Cargando datos…", { exact: true }),
    ).toHaveCount(0, { timeout: 15000 });
  }
  await page.goto("/learning");
  const learning = await (
    await page.request.get("/api/learning/status")
  ).json();
  if (learning.report)
    await expect(
      page.getByText("CATBOOST", { exact: true }).first(),
    ).toBeVisible();
  else
    await expect(
      page.getByText("Laboratorio listo para entrenar"),
    ).toBeVisible();
  await page.screenshot({ path: "../.runtime/model-lab.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("populated day supports top five, search, sorting and match detail", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/api/today") return route.fulfill({ json: scenario.today });
    if (path === "/api/settings")
      return route.fulfill({ json: scenario.settings });
    if (path === "/api/top")
      return route.fulfill({
        json:
          scenario.top[url.searchParams.get("market") ?? "OVER_2_5_GOALS"] ??
          [],
      });
    if (path === "/api/fixtures/1000")
      return route.fulfill({ json: scenario.detail });
    if (path === "/api/fixtures/1000/odds")
      return route.fulfill({ json: scenario.odds });
    if (path === "/api/fixtures/1000/analysis")
      return route.fulfill({ json: scenario.analysis });
    return route.continue();
  });
  await page.goto("/");
  await expect(page.locator(".pick-card")).toHaveCount(5);
  await expect(page.locator(".fixtures-table tbody tr")).toHaveCount(6);
  await page.screenshot({
    path: "../.runtime/today-scenario.png",
    fullPage: true,
  });
  await page.getByPlaceholder(/Buscar/).fill("Local 1");
  await expect(page.locator(".fixtures-table tbody tr")).toHaveCount(1);
  await page.getByPlaceholder(/Buscar/).fill("");
  await page
    .locator(".fixtures-table")
    .getByRole("button", { name: "O2.5", exact: true })
    .click();
  await page.goto("/match/1000");
  await expect(
    page.getByRole("heading", { name: "Lectura del partido" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Machine learning y deep learning" }),
  ).toBeVisible();
  await expect(page.locator(".score-matrix")).toBeVisible();
  await page.screenshot({
    path: "../.runtime/detail-scenario.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("layout remains usable on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/learning");
  await expect(page.getByRole("heading", { name: "Model lab." })).toBeVisible();
  await expect(page.getByText("Cargando datos…", { exact: true })).toHaveCount(
    0,
    {
      timeout: 15000,
    },
  );
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(392);
  await page.screenshot({ path: "../.runtime/mobile.png", fullPage: true });
});

test("progress shows running phases, training epochs and completion with warnings", async ({
  page,
}) => {
  const job = (
    kind: string,
    percent: number,
    stage: string,
    detail: string,
  ) => ({
    kind,
    running: true,
    status: "running",
    errors: [] as string[],
    started_at: new Date().toISOString(),
    progress: {
      percent,
      stage,
      detail,
      indeterminate: false,
      steps: [
        { key: kind, label: stage, status: "running", fraction: percent / 100 },
      ],
    },
  });
  const state = {
    job: job("fixtures", 37.5, "Forma reciente", "8/20 partidos revisados"),
    learning: job("training", 62, "Entrenar MLP", "MLP · época 12/35"),
  };
  await page.route("**/api/refresh/status", (route) =>
    route.fulfill({ json: state }),
  );
  await page.goto("/learning");
  await expect(
    page.getByRole("progressbar", { name: "Partidos, análisis y cuotas" }),
  ).toHaveAttribute("aria-valuenow", "37.5");
  await expect(
    page.getByRole("progressbar", { name: "Entrenamiento de modelos" }),
  ).toHaveAttribute("aria-valuenow", "62");
  await expect(page.getByText("MLP · época 12/35")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Model lab." })).toBeVisible();
  await page.screenshot({
    path: "../.runtime/progress-running.png",
    fullPage: true,
  });
  state.job.running = false;
  state.job.status = "partial";
  state.job.errors = ["Fuente de prueba temporalmente no disponible"];
  state.job.progress.percent = 100;
  state.job.progress.steps[0].status = "warning";
  state.job.progress.steps[0].fraction = 1;
  state.learning.running = false;
  state.learning.status = "complete";
  state.learning.progress.percent = 100;
  state.learning.progress.steps[0].status = "complete";
  state.learning.progress.steps[0].fraction = 1;
  await expect(
    page.getByRole("progressbar", { name: "Partidos, análisis y cuotas" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(
    page.getByText("Terminado con avisos", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Completado", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("progressbar", { name: "Progreso total" }),
  ).toHaveAttribute("aria-valuenow", "100");
  await expect(
    page.getByText("Actualización finalizada con avisos", { exact: true }),
  ).toBeVisible();
  await page.getByText("1 aviso · ver detalle").click();
  await expect(page.getByText(state.job.errors[0])).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(392);
  state.job.status = "complete";
  state.job.errors = [];
  state.job.progress.steps[0].status = "complete";
  await expect(
    page.getByText("MatchLab está preparado", { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveTitle("Actualización terminada · MatchLab");
});
