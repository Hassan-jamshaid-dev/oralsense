import { useState } from "react";
import { Link } from "react-router";
import { ArrowLeft, LogOut } from "lucide-react";
import { Alert } from "../../components/ui/Alert";
import { BrandMark } from "../../components/ui/BrandMark";
import { Button } from "../../components/ui/Button";
import { useDocumentTitle } from "../../lib/useDocumentTitle";
import { useAuth } from "../auth/authContext";
import { useSignOut } from "../auth/useSignOut";
import { CreateWorkspaceForm } from "./CreateWorkspaceForm";
import { EditWorkspaceForm } from "./EditWorkspaceForm";

export function WorkspaceSetupPage() {
  const { me } = useAuth();
  // Decided once on entry so creating a workspace doesn't swap this page into edit mode
  // while the success state is showing.
  const [mode] = useState<"create" | "edit">(() => (me?.workspace ? "edit" : "create"));
  const signOut = useSignOut();
  useDocumentTitle(mode === "edit" ? "Workspace details" : "Set up your workspace");

  if (me === null) return null;

  return (
    <div className="min-h-screen">
      <header className="border-b border-border">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-6">
          {mode === "edit" ? (
            <Link
              to="/app"
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium text-slate transition-colors hover:text-navy"
            >
              <ArrowLeft size={16} aria-hidden="true" />
              Back to dashboard
            </Link>
          ) : (
            <BrandMark />
          )}
          <div className="flex min-w-0 items-center gap-3">
            <span className="hidden truncate text-sm text-slate sm:block">{me.user.email}</span>
            <Button variant="ghost" size="sm" onClick={() => void signOut.signOut()} loading={signOut.pending}>
              {signOut.pending ? null : <LogOut size={16} aria-hidden="true" />}
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto w-full max-w-xl px-6 py-12 sm:py-16">
        {signOut.error ? (
          <Alert variant="error" title="Couldn't sign out" className="mb-8">
            {signOut.error}
          </Alert>
        ) : null}
        {mode === "edit" && me.workspace ? (
          <EditWorkspaceForm me={me} workspace={me.workspace} />
        ) : (
          <CreateWorkspaceForm me={me} />
        )}
      </main>
    </div>
  );
}
