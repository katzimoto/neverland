import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { api } from "./client";
import { getEntities } from "./documents";

vi.mock("./client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const apiGet = api.get as Mock;

beforeEach(() => {
  vi.clearAllMocks();
});

describe("documents API", () => {
  it("normalizes backend entity list responses for the insight UI", async () => {
    apiGet.mockResolvedValue([
      { id: "entity-1", name: "Acme Corp", type: "organization", frequency: 3 },
    ]);

    await expect(getEntities("doc-1")).resolves.toEqual({
      documant_id: "doc-1",
      entities: [{ label: "Acme Corp", type: "organization", count: 3 }],
    });
    expect(apiGet).toHaveBeenCalledWith("/documents/doc-1/entities");
  });

  it("preserves normalized entity envelope responses", async () => {
    apiGet.mockResolvedValue({
      documant_id: "doc-1",
      entities: [{ label: "Project Phoenix", type: "project", count: 2 }],
    });

    await expect(getEntities("doc-1")).resolves.toEqual({
      documant_id: "doc-1",
      entities: [{ label: "Project Phoenix", type: "project", count: 2 }],
    });
  });
});
