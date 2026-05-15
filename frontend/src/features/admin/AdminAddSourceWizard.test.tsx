import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { render } from "@/test/render";
import { AdminAddSourceWizard } from "./AdminAddSourceWizard";
import * as adminApi from "@/api/admin";

vi.mock("@/api/admin", () => ({
  adminApi: {
    connectorTypes: vi.fn(),
    listSources: vi.fn(),
    createSource: vi.fn(),
    listGroups: vi.fn(),
    grantPermission: vi.fn(),
  },
}));

const mockTypes = [
  {
    type: "folder",
    label: "Folder",
    fields: [
      { key: "path", label: "Folder path", required: true, sensitive: false, placeholder: "/data/docs" },
    ],
    supported_versions: {
      en: [{ value: "1.0", label: "1.0" }, { value: "2.0", label: "2.0" }],
      fr: [{ value: "1.0", label: "1.0" }],
    },
  },
  {
    type: "database",
    label: "Database",
    fields: [],
    supported_versions: {
      en: [{ value: "8.0", label: "8.0" }],
      he: [{ value: "8.0", label: "8.0" }, { value: "9.0", label: "9.0" }],
    },
  },
  {
    type: "hebrew-only",
    label: "Hebrew Only",
    fields: [],
    supported_versions: {
      he: [{ value: "1.0", label: "1.0" }],
    },
  },
  {
    type: "simple",
    label: "Simple",
    fields: [],
  },
];

beforeEach(() => {
  vi.mocked(adminApi.adminApi.connectorTypes).mockResolvedValue(mockTypes);
  vi.mocked(adminApi.adminApi.listGroups).mockResolvedValue([]);
});

describe("AdminAddSourceWizard", () => {
  it("shows connector type selection", async () => {
    render(<AdminAddSourceWizard />);
    expect(await screen.findByText("Folder")).toBeInTheDocument();
  });

  it("shows version dropdown with language-specific versions", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Folder");
    await user.click(screen.getByText("Folder"));
    const langSelect = screen.getByLabelText("Language");
    await user.selectOptions(langSelect, "fr");
    const versionSelect = screen.getByLabelText("Version");
    expect(versionSelect).toBeInTheDocument();
  });

  it("includes auto-detect as default version option", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Folder");
    await user.click(screen.getByText("Folder"));
    expect(screen.getByText("Auto detect")).toBeInTheDocument();
  });

  it("updates version options when language changes", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Folder");
    await user.click(screen.getByText("Folder"));
    const langSelect = screen.getByLabelText("Language");
    await user.selectOptions(langSelect, "en");
    expect(screen.getByText("2.0")).toBeInTheDocument();
    await user.selectOptions(langSelect, "fr");
    expect(screen.queryByText("2.0")).not.toBeInTheDocument();
  });

  it("shows English and Hebrew language options for connector with en and he", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Database");
    await user.click(screen.getByText("Database"));
    expect(screen.getByRole("option", { name: "English" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Hebrew" })).toBeInTheDocument();
  });

  it("defaults to he language for connector with only Hebrew support", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Hebrew Only");
    await user.click(screen.getByText("Hebrew Only"));
    expect(screen.getByLabelText("Language")).toHaveValue("he");
  });

  it("shows only English option and no version dropdown for connector without supported_versions", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Simple");
    await user.click(screen.getByText("Simple"));
    expect(screen.getByLabelText("Language")).toHaveValue("en");
    expect(screen.queryByLabelText("Version")).not.toBeInTheDocument();
  });

  it("resets language and version when switching connector type", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Folder");
    await user.click(screen.getByText("Folder"));
    await user.selectOptions(screen.getByLabelText("Language"), "fr");
    await user.selectOptions(screen.getByLabelText("Version"), "1.0");
    // There are two Back buttons (header + form); click the last one (form Back → type step)
    const backButtons = screen.getAllByRole("button", { name: /back/i });
    await user.click(backButtons[backButtons.length - 1]);
    await user.click(screen.getByText("Hebrew Only"));
    expect(screen.getByLabelText("Language")).toHaveValue("he");
    expect(screen.getByLabelText("Version")).toHaveValue("auto-detect");
  });

  it("resets version to auto-detect when changing to language that does not support current version", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Folder");
    await user.click(screen.getByText("Folder"));
    await user.selectOptions(screen.getByLabelText("Version"), "2.0");
    await user.selectOptions(screen.getByLabelText("Language"), "fr");
    expect(screen.getByLabelText("Version")).toHaveValue("auto-detect");
  });

  it("shows readable language label on the review screen", async () => {
    const user = userEvent.setup();
    render(<AdminAddSourceWizard />);
    await screen.findByText("Folder");
    await user.click(screen.getByText("Folder"));
    await user.type(screen.getByLabelText("Source name"), "My Source");
    await user.click(screen.getByRole("button", { name: /next: validate/i }));
    await user.click(screen.getByRole("button", { name: /skip validation/i }));
    await user.click(screen.getByRole("button", { name: /next: review/i }));
    const languageRow = screen.getByText("Language").closest("dt");
    expect(languageRow?.nextElementSibling?.textContent).toBe("English");
  });
});
