// ═══════════════════════════════════════════════════════════
// CS HUB — Interactive Layer
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

    // ───── 1. PAGE LOADER ─────
    const loader = document.getElementById('pageLoader');
    if (loader) {
        setTimeout(() => loader.classList.add('hidden'), 350);
    }

    // ───── 2. SCROLL REVEAL ─────
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll(
        '.card, .branch-card, .story-card, .signin-card, .topic-content > *,' +
        ' .auth-card, .profile-section, .stat-card, .branch-intro-card,' +
        ' .visitor-table, .profile-header'
    ).forEach(el => {
        el.classList.add('reveal-on-scroll');
        observer.observe(el);
    });

    // ───── 3. BACK TO TOP ─────
    const backBtn = document.getElementById('backToTop');
    if (backBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 400) backBtn.classList.add('visible');
            else backBtn.classList.remove('visible');
        }, { passive: true });
        backBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ───── 4. READING PROGRESS BAR ─────
    const article = document.querySelector('.topic-content');
    if (article) {
        const bar = document.createElement('div');
        bar.className = 'reading-progress';
        document.body.appendChild(bar);
        window.addEventListener('scroll', () => {
            const rect = article.getBoundingClientRect();
            const total = article.offsetHeight - window.innerHeight;
            const scrolled = Math.min(Math.max(-rect.top, 0), total);
            const pct = total > 0 ? (scrolled / total) * 100 : 0;
            bar.style.width = pct + '%';
        }, { passive: true });
    }

    // ───── 5. COMMAND PALETTE ─────
    const overlay = document.getElementById('cmdOverlay');
    const input = document.getElementById('cmdInput');
    const results = document.getElementById('cmdResults');
    const data = window.CS_HUB_DATA || { topics: [], branches: [] };

    const allItems = [
        { title: 'Home',            icon: '🏠', url: '/',           hint: 'page' },
        { title: 'All Topics',      icon: '📚', url: '/topics',     hint: 'page' },
        { title: 'Profile',         icon: '👤', url: '/profile',    hint: 'page' },
        { title: 'Visitors',        icon: '👥', url: '/visitors',   hint: 'page' },
        { title: 'Login',           icon: '🔑', url: '/login',      hint: 'page' },
        { title: 'Register',        icon: '✨', url: '/register',   hint: 'page' },
        { title: 'Logout',          icon: '🚪', url: '/logout',     hint: 'action' },
        ...data.branches.map(b => ({ title: b.title, icon: b.icon, url: b.url, hint: 'branch' })),
        ...data.topics.map(t  => ({ title: t.title, icon: t.icon, url: t.url, hint: 'topic'  })),
    ];

    let selectedIndex = 0;
    let filtered = allItems;

    function openCmd() {
        if (!overlay) return;
        overlay.classList.add('open');
        input.value = '';
        selectedIndex = 0;
        render('');
        setTimeout(() => input.focus(), 50);
    }
    function closeCmd() {
        overlay.classList.remove('open');
    }
    function render(query) {
        const q = query.toLowerCase().trim();
        filtered = allItems.filter(i =>
            !q || i.title.toLowerCase().includes(q) || i.hint.includes(q)
        ).slice(0, 8);

        if (!filtered.length) {
            results.innerHTML = '<li class="cmd-empty">No matches found</li>';
            return;
        }
        results.innerHTML = filtered.map((item, i) => `
            <li class="${i === selectedIndex ? 'active' : ''}" data-index="${i}">
                <span class="cmd-icon">${item.icon}</span>
                <span class="cmd-title">${item.title}</span>
                <span class="cmd-hint">${item.hint}</span>
            </li>
        `).join('');
    }

    if (overlay && input) {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                overlay.classList.contains('open') ? closeCmd() : openCmd();
            }
            if (e.key === 'Escape' && overlay.classList.contains('open')) closeCmd();
            if (!overlay.classList.contains('open')) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, filtered.length - 1);
                render(input.value);
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                render(input.value);
            }
            if (e.key === 'Enter' && filtered[selectedIndex]) {
                window.location.href = filtered[selectedIndex].url;
            }
        });
        input.addEventListener('input', (e) => {
            selectedIndex = 0;
            render(e.target.value);
        });
        results.addEventListener('click', (e) => {
            const li = e.target.closest('li[data-index]');
            if (li && filtered[li.dataset.index]) {
                window.location.href = filtered[li.dataset.index].url;
            }
        });
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeCmd();
        });
    }

    // ───── 6. CONFETTI ─────
    const canvas = document.getElementById('confettiCanvas');
    if (canvas && (window.location.search.includes('welcome=1') || document.querySelector('.flash-success'))) {
        launchConfetti();
    }
    function launchConfetti() {
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const colors = ['#b8ff3c', '#22d3ee', '#8b5cf6', '#ff6b5b', '#ec4899'];
        const particles = Array.from({ length: 120 }, () => ({
            x: Math.random() * canvas.width,
            y: -20,
            vx: (Math.random() - 0.5) * 4,
            vy: Math.random() * 3 + 2,
            size: Math.random() * 6 + 3,
            color: colors[Math.floor(Math.random() * colors.length)],
            rot: Math.random() * Math.PI,
            rotSpeed: (Math.random() - 0.5) * 0.2,
            life: 0,
        }));
        let frames = 0;
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.05;
                p.rot += p.rotSpeed;
                p.life++;
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate(p.rot);
                ctx.fillStyle = p.color;
                ctx.globalAlpha = Math.max(0, 1 - p.life / 200);
                ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
                ctx.restore();
            });
            frames++;
            if (frames < 220) requestAnimationFrame(animate);
            else ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        animate();
    }

    // ───── 7. SUBTLE PARALLAX ON HERO ─────
    const hero = document.querySelector('.welcome-hero, .intro-hero, .branch-header');
    if (hero) {
        window.addEventListener('scroll', () => {
            const y = window.scrollY;
            if (y < 800) hero.style.transform = `translateY(${y * 0.15}px)`;
        }, { passive: true });
    }

    // ───── 8. KEYBOARD: PRESS "/" TO OPEN COMMAND PALETTE ─────
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            openCmd();
        }
    });
    // ───── 9. TABLE OF CONTENTS ─────
    const tocList = document.getElementById('tocList');
    const content = document.getElementById('topicContent');
    if (tocList && content) {
        const headings = content.querySelectorAll('h3');
        if (headings.length === 0) {
            document.getElementById('toc').style.display = 'none';
        } else {
            headings.forEach((h, i) => {
                const id = 'heading-' + i;
                h.id = id;
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#' + id;
                a.textContent = h.textContent;
                li.appendChild(a);
                tocList.appendChild(li);
            });

            // Highlight active heading on scroll
            const tocLinks = tocList.querySelectorAll('a');
            window.addEventListener('scroll', () => {
                let current = '';
                headings.forEach(h => {
                    if (h.getBoundingClientRect().top < 140) current = h.id;
                });
                tocLinks.forEach(a => {
                    a.classList.toggle('active', a.getAttribute('href') === '#' + current);
                });
            }, { passive: true });
        }
    }
});