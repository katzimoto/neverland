import { beforeEach, test, expect, vi } from "vitest";
import { fireEvent, screen, render } from "@/test/render";
import { HistoryPage } from "./HistoryPage";

const mocks = vi.hoisted(() => ({
  getActivity: vi.fn(),
}));

vi.mock("@/api/history", () => ({ getActivity: mocks.getActivity }));
vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }));

beforeEach(() => {
  mocks.getActivity.mockReset();
  mocks.getActivity.mockResolvedValue([]);
});

test("shows history privacy note", async () => {
  render(<HistoryPage />);
  expect(
    screen.getByText("Activity visible only to you and admins.")
  ).toBeInTheDocument();
  expect(await screen.findByText("No history")).toBeInTheDocument();
});

test("loads history in pages when more activity exists", async () => {
  const firstPage = Array.from({ length: 50 }, (_, i) => ({
    document_id: `doc-${i}`,
    title: `Document ${i}`,
    mime_type: "text/plain",
    viewed_at: "2026-05-10T00:00:00Z",
  }));
  mocks.getActivity
    .mockResolvedValueOnce(firstPage)
    .mockResolvedValueOnce([
      {
        document_id: "doc-50",
        title: "Document 50",
        mime_type: "application/pdf",
        viewed_at: null,
      },
    ]);

  render(<HistoryPage />);

  expect(await screen.findByText("Document 0")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Load more history" }));

  expect(await screen.findByText("Document 50")).toBeInTheDocument();
  expect(mocks.getActivity).toHaveBeenNthCalledWith(1, 50, 0);
  expect(mocks.getActivity).toHaveBeenNthCalledWith(2, 50, 50);
});
