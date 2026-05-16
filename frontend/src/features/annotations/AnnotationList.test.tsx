import { beforeEach, test, expect, vi } from "vitest";
import { screen, render } from "@/test/render";
import { ApiError } from "@/api/client";
import { AnnotationList } from "./AnnotationList";

const mocks = vi.hoisted(() => ({
  listAnnotations: vi.fn(),
}));

vi.mock("@/api/auth", () => ({
  getCurrentUser: vi.fn(() =>
    Promise.resolve({
      user_id: "u1",
      email: "a@example.com",
      display_name: "Ari",
      is_admin: false,
      groups: [],
    })
  ),
}));
vi.mock("@/api/annotations", () => ({
  listAnnotations: mocks.listAnnotations,
  createAnnotation: vi.fn(),
}));

beforeEach(() => {
  mocks.listAnnotations.mockReset();
});

test("renders annotation permission state without leaking document id", async () => {
  mocks.listAnnotations.mockRejectedValueOnce(new ApiError(403, "Forbidden"));

  render(<AnnotationList docId="secret-doc" />);
  expect(
    await screen.findByText("Annotations unavailable")
  ).toBeInTheDocument();
  expect(screen.queryByText("secret-doc")).not.toBeInTheDocument();
});

test("renders annotations mapped from the backend envelope", async () => {
  mocks.listAnnotations.mockResolvedValueOnce([
    {
      id: "a1",
      document_id: "d1",
      author_id: "u1",
      author_name: "Ari",
      body: "Shared backend note",
      position: { page: 2 },
      shared: true,
      created_at: "2026-05-01T10:00:00Z",
      updated_at: "2026-05-01T11:00:00Z",
    },
    {
      id: "a2",
      document_id: "d1",
      author_id: "u2",
      author_name: "Bo",
      body: "Private backend note",
      position: null,
      shared: false,
      created_at: "2026-05-01T10:00:00Z",
      updated_at: "2026-05-01T11:00:00Z",
    },
  ]);

  render(<AnnotationList docId="d1" />);

  expect(await screen.findByText("Shared backend note")).toBeInTheDocument();
  expect(screen.getByText("Shared with readers")).toBeInTheDocument();
  expect(screen.getByText("Private backend note")).toBeInTheDocument();
  expect(screen.getByText("Private note")).toBeInTheDocument();
});
