import { test, expect } from "@playwright/test";
import { seedSession } from "./phase08e-fixtures";

const searchResults = {
  total: 2,
  query: "vendor risk",
  results: [
    {
      doc_id: "doc-1",
      source_id: "src-1",
      external_id: null,
      title: "Vendor Risk Assessment 2024",
      snippet: "This document covers the annual vendor risk assessment process.",
      source: "confluence",
      source_label: "Confluence",
      mime_type: "application/pdf",
      tags: ["risk", "vendor"],
      translation_quality: null,
      score: 0.92,
      updated_at: "2026-05-10T00:00:00Z",
      indexed_at: "2026-05-10T00:00:00Z",
      why: [{ kind: "term", label: 'Matched "vendor risk" in title' }],
    },
    {
      doc_id: "doc-2",
      source_id: "src-1",
      external_id: null,
      title: "Supplier Security Notes",
      snippet: "Follow-up notes for supplier security reviews.",
      source: "folder",
      source_label: "Folder",
      mime_type: "text/plain",
      tags: ["security"],
      translation_quality: null,
      score: 0.81,
      updated_at: "2026-05-10T00:00:00Z",
      indexed_at: "2026-05-10T00:00:00Z",
      why: [],
    },
  ],
};

test.describe("Search keyboard workflow", () => {
  test("selects, previews, and opens results without a mouse", async ({ page }) => {
    await seedSession(page);
    await page.route("**/api/search", (route) => route.fulfill({ json: searchResults }));
    await page.goto("/search");

    await page.getByRole("searchbox", { name: "Search" }).blur();
    await page.keyboard.press("/");
    await expect(page.getByRole("searchbox", { name: "Search" })).toBeFocused();

    await page.getByRole("searchbox", { name: "Search" }).fill("vendor risk");
    await page.keyboard.press("Enter");
    await expect(page.getByText("Vendor Risk Assessment 2024")).toBeVisible();

    const results = page.getByRole("listbox", { name: "Search results" });
    await results.focus();
    await page.keyboard.press("j");
    await expect(page.getByRole("option", { name: /Supplier Security Notes/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );

    await page.keyboard.press("Space");
    await expect(page.getByRole("dialog", { name: "Supplier Security Notes" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Supplier Security Notes" })).toBeHidden();
    await expect(results).toBeFocused();

    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/doc\/doc-2/);
  });
});
