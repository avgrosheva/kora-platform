/** Kora design tokens — Tailwind theme extension. */
module.exports = {
  colors: {
    ink: {
      950: '#05070A', // app background
      900: '#070A0F', // sidebar top
      850: '#0A0F16', // popovers, chat, modals
      800: '#070A0E', // chat bottom gradient
    },
    accent: {
      DEFAULT: '#4D8DFF',
      bright: '#5C9BFF',
      soft: '#7FB0FF',
      pale: '#9FC2FF',
      ghost: '#8FB3F0',
      deep: '#1B4FB0',
      ink: '#0A1220', // text on a filled accent button
    },
    fg: {
      DEFAULT: '#E7EBF1',
      secondary: '#DCE3EC',
      tertiary: '#C9D2DD',
      quiet: '#9AA5B2',
      muted: '#8B95A2',
      dim: '#79838F',
      faint: '#5B6675',
      ghost: '#3F4855',
      disabled: '#4A535F',
    },
    danger: { DEFAULT: '#FF5C5C', soft: '#FF8A8A', pale: '#FFB4B4', wash: '#FFC9C9', ink: '#FFD4D4' },
    warn:   { DEFAULT: '#F2B24C', soft: '#FFCF80', pale: '#FFD79A', wash: '#F5DFB4' },
    good:   { DEFAULT: '#46D9A0', pale: '#B6EFD8', wash: '#DCEFE6' },
  },
  fontFamily: {
    sans: ['Geist', 'system-ui', '-apple-system', 'sans-serif'],
    mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
  },
  letterSpacing: {
    label: '0.14em',  // mono section labels
    kicker: '0.16em', // breadcrumbs / eyebrows
    badge: '0.08em',
    tight: '-0.9px',  // page headings
  },
  boxShadow: {
    'glow-accent': '0 0 26px -8px rgba(77,141,255,0.9)',
    'glow-accent-lg': '0 0 40px -10px rgba(77,141,255,0.95)',
    'glow-danger': '0 0 10px rgba(255,92,92,0.8)',
    'glow-warn': '0 0 10px rgba(242,178,76,0.8)',
    'glow-good': '0 0 10px rgba(70,217,160,0.6)',
    'panel-pop': '0 24px 60px -20px rgba(0,0,0,0.9), 0 0 40px -24px rgba(77,141,255,0.6)',
    'modal': '0 40px 100px -30px rgba(0,0,0,0.95), 0 0 70px -34px rgba(77,141,255,0.6)',
    'chat': '0 30px 80px -20px rgba(0,0,0,0.9), 0 0 60px -30px rgba(77,141,255,0.55)',
  },
  backgroundImage: {
    'panel-sheen': 'linear-gradient(180deg,rgba(255,255,255,0.035),rgba(255,255,255,0.012))',
    'hero-accent': 'linear-gradient(135deg,rgba(29,76,158,0.16),rgba(255,255,255,0.015) 55%)',
    'hero-warn': 'linear-gradient(135deg,rgba(242,178,76,0.07),rgba(255,255,255,0.012) 60%)',
    'accent-btn': 'linear-gradient(180deg,#7FB0FF,#4D8DFF)',
    'accent-rail': 'linear-gradient(90deg,rgba(77,141,255,0.16),rgba(77,141,255,0.03))',
    'sidebar': 'linear-gradient(180deg,#070A0F 0%,#05070A 100%)',
  },
};
