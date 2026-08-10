/**
 * RecoPulse Executive Theme Engine
 * Controls Dark Mode / Light Mode switching across all storefronts, home page, and merchant dashboard.
 * Uses event delegation and clean SVG icons (Moon for Light Mode, Sun for Dark Mode).
 */
class ThemeEngine {
    constructor() {
        this.themeKey = 'recopulse_theme_preference';
        this.init();
    }

    init() {
        const savedTheme = localStorage.getItem(this.themeKey) || 'dark';
        this.applyTheme(savedTheme);

        // Global Event Delegation for Theme Toggle Buttons
        document.addEventListener('click', (e) => {
            const toggleBtn = e.target.closest('.theme-toggle-btn, [data-theme-toggle]');
            if (toggleBtn) {
                e.preventDefault();
                e.stopPropagation();
                this.toggleTheme();
            }
        });

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.updateToggleUI(this.getTheme()));
        } else {
            this.updateToggleUI(this.getTheme());
        }
    }

    getTheme() {
        return localStorage.getItem(this.themeKey) || 'dark';
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);

        if (theme === 'dark') {
            document.documentElement.classList.add('dark-theme');
            document.body.classList.add('dark-theme');
            document.documentElement.classList.remove('light-theme');
            document.body.classList.remove('light-theme');
        } else {
            document.documentElement.classList.remove('dark-theme');
            document.body.classList.remove('dark-theme');
            document.documentElement.classList.add('light-theme');
            document.body.classList.add('light-theme');
        }

        localStorage.setItem(this.themeKey, theme);
        this.updateToggleUI(theme);
    }

    toggleTheme() {
        const current = this.getTheme();
        const next = current === 'dark' ? 'light' : 'dark';
        this.applyTheme(next);
    }

    updateToggleUI(theme) {
        const btns = document.querySelectorAll('.theme-toggle-btn, [data-theme-toggle]');
        btns.forEach(btn => {
            if (theme === 'light') {
                // In Light Mode: Button allows switching to Dark Mode
                btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg><span>Dark Mode</span>`;
                btn.setAttribute('title', 'Switch to Dark Mode');
                btn.setAttribute('aria-label', 'Switch to Dark Mode');
                btn.classList.add('is-light');
                btn.classList.remove('is-dark');
            } else {
                // In Dark Mode: Button allows switching to Light Mode
                btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg><span>Light Mode</span>`;
                btn.setAttribute('title', 'Switch to Light Mode');
                btn.setAttribute('aria-label', 'Switch to Light Mode');
                btn.classList.add('is-dark');
                btn.classList.remove('is-light');
            }
        });
    }
}

// Global Singleton Instance
window.themeEngine = new ThemeEngine();
