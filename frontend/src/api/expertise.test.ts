import { beforeEach, expect, test, vi } from "vitest";
import { api } from "./client";
import { getExpertise } from "./expertise";

vi.mock("./client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const get = vi.mocked(api.get);

beforeEach(() => {
  get.mockReset();
});

test("requests expertise with the backend topic query param and raw list response", async () => {
  const response = [{ user_id: "u1", display_name: "Ari", score: 1.4, signals: { views: 2, comments: 1, annotations: 0, subscriptions: 1 }, reason: "Has activity on matching documents", top_docs: [{ documantions_id: "d1", title: "Risk memo", score: 0.9 }] }];
  get.mockResolvedValueOnce(response);

  await expect(getExpertise("incident response")).resolves.toBe(response);

  expect(get).toHaveBeenCalledWith("/expertise?topic=incident+response");
});
