document.addEventListener('DOMContentLoaded', () => {
    initUserMenu();
    initDashboardSidebar();
});

function initUserMenu() {
    const userMenu = document.querySelector('.user-menu');
    const userAvatar = document.querySelector('.user-menu .user-avatar');
    const userDropdown = document.getElementById('userDropdown');

    if (!userMenu || !userAvatar || !userDropdown) {
        return;
    }

    const closeUserDropdown = () => {
        userDropdown.classList.remove('show');
    };

    const toggleUserDropdown = () => {
        userDropdown.classList.toggle('show');
    };

    userAvatar.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleUserDropdown();
    });

    userDropdown.addEventListener('click', (event) => {
        event.stopPropagation();
    });

    document.addEventListener('click', (event) => {
        if (!userMenu.contains(event.target)) {
            closeUserDropdown();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeUserDropdown();
        }
    });
}

function initDashboardSidebar() {
    const dashboardContainer = document.querySelector('.dashboard-container');
    const sidebar = document.querySelector('.dashboard-container .sidebar');

    if (!dashboardContainer || !sidebar) {
        return;
    }

    let toggle = document.querySelector('.dashboard-sidebar-toggle');
    let overlay = document.querySelector('.dashboard-sidebar-overlay');

    if (!sidebar.id) {
        sidebar.id = 'dashboard-sidebar';
    }

    if (!toggle) {
        toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'dashboard-sidebar-toggle dashboard-sidebar-toggle-generated';
        toggle.setAttribute('aria-label', 'Abrir menu');
        toggle.setAttribute('aria-controls', sidebar.id);
        toggle.innerHTML = '<span></span><span></span><span></span>';

        const topHeader = dashboardContainer.querySelector('.top-header');
        const mainContent = dashboardContainer.querySelector('.main-content');
        if (topHeader) {
            topHeader.insertBefore(toggle, topHeader.firstChild);
        } else if (mainContent) {
            mainContent.insertBefore(toggle, mainContent.firstChild);
        } else {
            dashboardContainer.insertBefore(toggle, dashboardContainer.firstChild);
        }
    }

    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'dashboard-sidebar-overlay';
        overlay.hidden = true;
        dashboardContainer.insertAdjacentElement('afterend', overlay);
    }

    const closeSidebar = () => {
        sidebar.classList.remove('is-open');
        overlay.classList.remove('is-visible');
        overlay.hidden = true;
        document.body.classList.remove('dashboard-sidebar-open');
        toggle.setAttribute('aria-expanded', 'false');
    };

    const openSidebar = () => {
        sidebar.classList.add('is-open');
        overlay.hidden = false;
        requestAnimationFrame(() => overlay.classList.add('is-visible'));
        document.body.classList.add('dashboard-sidebar-open');
        toggle.setAttribute('aria-expanded', 'true');
    };

    toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', () => {
        if (sidebar.classList.contains('is-open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    overlay.addEventListener('click', closeSidebar);
    sidebar.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', closeSidebar);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeSidebar();
        }
    });

    if (typeof window.matchMedia !== 'function') {
        return;
    }

    const desktopQuery = window.matchMedia('(min-width: 1025px)');
    const handleDesktopChange = (event) => {
        if (event.matches) {
            closeSidebar();
        }
    };

    if (typeof desktopQuery.addEventListener === 'function') {
        desktopQuery.addEventListener('change', handleDesktopChange);
    } else {
        desktopQuery.addListener(handleDesktopChange);
    }
}
