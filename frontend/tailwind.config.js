/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        void:   '#050810',
        panel:  'rgba(13,18,30,0.85)',
        border: 'rgba(35,50,70,0.8)',
        surface: {
          DEFAULT:   '#050810',
          secondary: '#0d1220',
          tertiary:  '#131b2e',
          elevated:  '#1a2540',
          border:    '#1e2d45',
        },
        accent: {
          blue:   '#2d7dd2',
          violet: '#7c3aed',
          cyan:   '#06b6d4',
          green:  '#10b981',
          orange: '#f97316',
        },
        rarity: {
          common:    '#9E9E9E',
          uncommon:  '#4CAF50',
          rare:      '#2196F3',
          epic:      '#9C27B0',
          legendary: '#FFD700',
        },
        metal:    '#94a3b8',
        crystal:  '#7dd3fc',
        deuterium:'#86efac',
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Consolas', 'monospace'],
        display: ['Orbitron', 'sans-serif'],
      },
      animation: {
        'pulse-slow':  'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'glow':        'glow 2s ease-in-out infinite alternate',
        'slide-up':    'slideUp 0.25s ease-out',
        'fade-in':     'fadeIn 0.3s ease-out',
        'float':       'float 4s ease-in-out infinite',
        'scan':        'scan 4s linear infinite',
        'pulse-glow':  'pulseGlow 2.5s ease-in-out infinite',
      },
      keyframes: {
        glow:      { from: { boxShadow: '0 0 5px currentColor' }, to: { boxShadow: '0 0 20px currentColor, 0 0 40px currentColor' } },
        slideUp:   { from: { transform: 'translateY(10px)', opacity: '0' }, to: { transform: 'translateY(0)', opacity: '1' } },
        fadeIn:    { from: { opacity: '0' }, to: { opacity: '1' } },
        float:     { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-6px)' } },
        scan:      { '0%': { transform: 'translateY(-100%)' }, '100%': { transform: 'translateY(400%)' } },
        pulseGlow: { '0%,100%': { opacity: '0.6' }, '50%': { opacity: '1' } },
      },
      backdropBlur: { xs: '2px', sm: '8px', md: '16px' },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-space':  'linear-gradient(180deg, #050810 0%, #0a0f1e 100%)',
      },
      boxShadow: {
        'glow-blue':   '0 0 20px rgba(45,125,210,0.4)',
        'glow-violet': '0 0 20px rgba(124,58,237,0.4)',
        'glow-cyan':   '0 0 20px rgba(6,182,212,0.4)',
        'glow-gold':   '0 0 20px rgba(255,215,0,0.4), 0 0 40px rgba(255,215,0,0.15)',
      },
    },
  },
  plugins: [],
}
