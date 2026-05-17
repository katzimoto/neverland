import { beforeEach, test, expect, vi } from "vitest";
import { screen, render } from "@/test/render";
import { ApiError } from "@/api/client";
import { CommentList } from "./CommentList";

const mocks = vi.hoisted(() => ({
  listComments: vi.fn(),
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
vi.mock("@/api/comments", () => ({
  listComments: mocks.listComments,
  createComment: vi.fn(),
}));

beforeEach(() => {
  mocks.listComments.mockReset();
});

test("renders permission state without a document title", async () => {
  mocks.listComments.mockRejectedValueOnce(new ApiError(403, "Forbidden"));

  render(<CommentList docId="secret-doc" />);
  expect(await screen.findByText("Comments unavailable")).toBeInTheDocument();
  expect(screen.queryByText("secret-doc")).not.toBeInTheDocument();
});

test("renders comments mapped from the backend envelope", async () => {
  mocks.listComments.mockResolvedValueOnce([
    {
      id: "c1",
      documant_id: "d1",
      author_id: "u1",
      author_name: "Ari",
      body: "Backend envelope comment",
      created_at: "2026-05-01T10:00:00Z",
      updated_at: "2026-05-01T11:00:00Z",
    },
  ]);

  render(<CommentList docId="d1" />);

  expect(await screen.findByLabelText("Comment by Ari")).toBeInTheDocument();
  expect(screen.getByText("Backend envelope comment")).toBeInTheDocument();
  expect(screen.getByText(/Edited/)).toBeInTheDocument();
});
