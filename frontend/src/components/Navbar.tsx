import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { ShieldCheck, BarChart3 } from "lucide-react";

export function Navbar() {
  const location = useLocation();

  const links = [
    { to: "/fact-check", label: "Fact Check", icon: ShieldCheck },
    { to: "/dashboard", label: "Evaluation Dashboard", icon: BarChart3 },
  ];

  return (
    <nav className="border-b border-border bg-card shadow-sm">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg text-foreground">
            KG Fact-Checker
          </span>
        </div>
        <div className="flex gap-1">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                location.pathname === link.to
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <link.icon className="h-4 w-4" />
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

