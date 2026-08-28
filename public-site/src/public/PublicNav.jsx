import { useState } from "react";
import { Menu } from "lucide-react";
import { app } from "../config.js";
import { Button } from "../components/ui/button.jsx";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../components/ui/sheet.jsx";

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/features", label: "Features" },
  { to: "/pricing", label: "Pricing" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

export default function PublicNav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur">
      <div className="market-wrap flex h-16 items-center justify-between gap-4">
        <a href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-base font-black text-primary-foreground">
            V
          </span>
          <span className="text-lg font-extrabold tracking-tight text-foreground">
            Vahan<span className="text-primary">Khata</span>
          </span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex">
          {LINKS.map((l) => (
            <a
              key={l.to}
              href={l.to}
              className="rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-accent hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <Button asChild variant="ghost">
            <a href={app("/")}>Log in</a>
          </Button>
          <Button asChild>
            <a href="/request-demo">Start free trial</a>
          </Button>
        </div>

        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="lg:hidden"
              aria-label="Toggle menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-72">
            <SheetHeader className="mb-4">
              <SheetTitle className="text-left">VahanKhata</SheetTitle>
            </SheetHeader>
            <nav className="flex flex-col gap-1">
              {LINKS.map((l) => (
                <a
                  key={l.to}
                  href={l.to}
                  onClick={() => setOpen(false)}
                  className="rounded-md px-3 py-2.5 text-sm font-medium text-muted-foreground transition hover:bg-accent hover:text-foreground"
                >
                  {l.label}
                </a>
              ))}
              <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
                <Button asChild variant="outline" className="w-full">
                  <a href={app("/")} onClick={() => setOpen(false)}>
                    Log in
                  </a>
                </Button>
                <Button asChild className="w-full">
                  <a href="/request-demo" onClick={() => setOpen(false)}>
                    Start free trial
                  </a>
                </Button>
              </div>
            </nav>
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}