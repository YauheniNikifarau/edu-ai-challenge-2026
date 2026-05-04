import { Outlet, createRootRoute, HeadContent, Scripts } from "@tanstack/react-router";
import { HelmetProvider } from "react-helmet-async";

import appCss from "../styles.css?url";
import { AuthProvider } from "@/lib/auth";
import { TopNav } from "@/components/TopNav";
import { Toaster } from "@/components/ui/sonner";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Evently — Host & attend community events" },
      { name: "description", content: "Discover, host, and attend community events with Evently." },
      { property: "og:title", content: "Evently — Host & attend community events" },
      { property: "og:description", content: "Discover, host, and attend community events with Evently." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "twitter:title", content: "Evently — Host & attend community events" },
      { name: "twitter:description", content: "Discover, host, and attend community events with Evently." },
      { property: "og:image", content: "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/52bbf30c-d72b-4425-ab62-a6bd89577e24/id-preview-6051ea76--5b8e6b39-6372-4075-bf21-85f37911cba4.lovable.app-1777924075419.png" },
      { name: "twitter:image", content: "https://pub-bb2e103a32db4e198524a2e9ed8f35b4.r2.dev/52bbf30c-d72b-4425-ab62-a6bd89577e24/id-preview-6051ea76--5b8e6b39-6372-4075-bf21-85f37911cba4.lovable.app-1777924075419.png" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  return (
    <HelmetProvider>
      <AuthProvider>
        <div className="min-h-screen bg-background">
          <TopNav />
          <Outlet />
          <Toaster />
        </div>
      </AuthProvider>
    </HelmetProvider>
  );
}
