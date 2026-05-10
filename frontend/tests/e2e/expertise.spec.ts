import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { seedSession } from "./phase08e-fixtures";

test("expertise route uses evidence language and command menu navigates", async ({ page }) => {
  await seedSession(page);
  await page.route("**/api/expertise?topic=risk", (route) => route.fulfill({ json: [{ user_id: "u1", display_name: "Ari", score: 1.4, signals: { views: 2, comments: 1, annotations: 0, subscriptions: 1 }, reason: "Has activity on matching documents", top_docs: [{ doc_id: "d1", title: "Risk memo", score: 0.9 }] }] }));
  await page.goto("/expertise");
  await page.getByLabel("Topic").fill("risk");
  await page.getByRole("button", { name: "Find evidence" }).click();
  await expect(page.getByText("Evidence, not ranking")).toBeVisible();
  await expect(page.getByText("Risk memo")).toBeVisible();
  await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
  await page.getByPlaceholder("Type a destination…").fill("history");
  await expect(page.getByRole("button", { name: "History" })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
