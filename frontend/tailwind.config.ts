import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";
// eslint-disable-next-line @typescript-eslint/no-var-requires
const koraTokens = require("./tailwind.config.tokens");

// `koraTokens.colors.accent` (the redesign's brand blue) and our existing
// shadcn `colors.accent` (an hsl(var(--accent)) hover-state color) share a
// key. A plain object-literal merge below would let the later spread win
// and silently drop `accent.foreground`, which shadcn's still-unmigrated
// components (DropdownMenuItem, etc.) read as `text-accent-foreground` —
// so `accent` is merged one level deeper than the rest: the redesign's
// DEFAULT/bright/soft/pale/ghost/deep/ink shades apply, `foreground` is
// kept from the existing theme so nothing unmigrated loses its hover state.
const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      ...koraTokens,
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        ...koraTokens.colors,
        accent: {
          foreground: "hsl(var(--accent-foreground))",
          ...koraTokens.colors.accent,
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;