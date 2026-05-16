import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { seedSession } from "./phase08e-fixtures";

test("annotations private and shared labels are represented in collaboration UI", async ({ page }) => {
  await seedSession(page);
  await page.route("**/api/expertise?topic=privacy", (route) => route.fulfill({ json: [{ user_id: "u1", display_name: "Ari", score: 1.4, signals: { views: 1, comments: 0, annotations: 2, subscriptions: 0 }, reason: "Has activity on matching documents", top_docs: [{ documant_id: "d1", title: "Private note", score: 0.9 }, { documant_id: "d2", title: "Shared with readers", score: 0.8 }] }] }));
  await page.goto("/expertise");
  await page.getByLabel("Topic").fill("privacy");
  await page.getByRole("button", { name: "Find evidence" }).click();
  await expect(page.getByText("Private note").first()).toBeVisible();
  await expect(page.getByText("Shared with readers").first()).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
