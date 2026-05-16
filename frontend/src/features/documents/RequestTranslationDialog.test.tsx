import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render as tlRender } from "@testing-library/react";
import { ToastProvider } from "@/components/primitives/Toast";
import { LanguageProvider } from "@/i18n/LanguageProvider";
import { RequestTranslationDialog } from "./RequestTranslationDialog";
import * as documentsApi from "@/api/documents";

vi.mock("@/api/documents");
vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));

function renderWithClient(ui: React.ReactElement, queryClient: QueryClient) {
  return tlRender(ui, {
    wrapper: ({ children }) => (
      <LanguageProvider>
        <QueryClientProvider client={queryClient}>
          <ToastProvider>{children}</ToastProvider>
        </QueryClientProvider>
      </LanguageProvider>
    ),
  });
}

beforeEach(() => {
  vi.mocked(documentsApi.requestTranslation).mockResolvedValue({
    documant_id: "doc-1",
    translation_version_id: "v-new",
    status: "pending",
  });
});

describe("RequestTranslationDialog", () => {
  it("renders dialog when open", () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    renderWithClient(
      <RequestTranslationDialog docId="doc-1" open onClose={vi.fn()} />,
      qc
    );
    expect(
      screen.getByRole("heading", { name: /request high-quality translation/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /request translation/i })
    ).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    renderWithClient(
      <RequestTranslationDialog docId="doc-1" open={false} onClose={vi.fn()} />,
      qc
    );
    expect(
      screen.queryByRole("heading", {
        name: /request high-quality translation/i,
      })
    ).not.toBeInTheDocument();
  });

  it("calls onClose when Cancel is clicked", () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const onClose = vi.fn();
    renderWithClient(
      <RequestTranslationDialog docId="doc-1" open onClose={onClose} />,
      qc
    );
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("submits request and shows success state", async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    renderWithClient(
      <RequestTranslationDialog docId="doc-1" open onClose={vi.fn()} />,
      qc
    );
    fireEvent.click(
      screen.getByRole("button", { name: /request translation/i })
    );
    await waitFor(() => {
      expect(documentsApi.requestTranslation).toHaveBeenCalledWith("doc-1");
    });
  });

  it("invalidates doc-translation-versions query after successful request", async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const invalidateSpy = vi.spyOn(qc, "invalidateQueries");
    renderWithClient(
      <RequestTranslationDialog docId="doc-1" open onClose={vi.fn()} />,
      qc
    );
    fireEvent.click(
      screen.getByRole("button", { name: /request translation/i })
    );
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ["doc-translation-versions", "doc-1"],
        })
      );
    });
  });
});
