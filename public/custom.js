(function () {
    function playSend() {
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            ctx.resume().then(function () {
                var osc = ctx.createOscillator(), gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.setValueAtTime(440, ctx.currentTime);
                osc.frequency.linearRampToValueAtTime(520, ctx.currentTime + 0.06);
                gain.gain.setValueAtTime(0.04, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
                osc.start(); osc.stop(ctx.currentTime + 0.1);
            });
        } catch (e) {}
    }

    function playDone() {
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            ctx.resume().then(function () {
                [[660, 0], [880, 0.12]].forEach(function (p) {
                    var osc = ctx.createOscillator(), gain = ctx.createGain();
                    osc.connect(gain); gain.connect(ctx.destination);
                    osc.type = 'sine'; osc.frequency.value = p[0];
                    var t = ctx.currentTime + p[1];
                    gain.gain.setValueAtTime(0.05, t);
                    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.4);
                    osc.start(t); osc.stop(t + 0.4);
                });
            });
        } catch (e) {}
    }

    function hideThemeToggle() {
        var header = document.getElementById('header');
        if (!header) return;
        header.querySelectorAll('button').forEach(function(btn) {
            var svg = btn.querySelector('svg');
            if (!svg) return;
            var testId = (svg.getAttribute('data-testid') || '').toLowerCase();
            var label = (btn.getAttribute('aria-label') || btn.getAttribute('title') || '').toLowerCase();
            if (testId.includes('mode') || label.includes('theme') || label.includes('dark') || label.includes('light')) {
                btn.style.display = 'none';
            }
        });
    }
    hideThemeToggle();
    setTimeout(hideThemeToggle, 500);
    setTimeout(hideThemeToggle, 2000);

    function getFirstName() {
        try {
            var token = localStorage.getItem('token');
            if (token) {
                var parts = token.split('.');
                if (parts.length >= 2) {
                    var padded = parts[1].replace(/-/g, '+').replace(/_/g, '/');
                    while (padded.length % 4) padded += '=';
                    var payload = JSON.parse(atob(padded));
                    var id = payload.identifier || payload.sub || '';
                    if (id.includes('@')) id = id.split('@')[0];
                    if (id) return id.charAt(0).toUpperCase() + id.slice(1);
                }
            }
        } catch(e) {}
        return '';
    }

    var _greetingText = (function() {
        var hour = new Date().getHours();
        var period = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';
        var name = getFirstName();
        return name ? 'Good ' + period + ', ' + name + '.' : 'Good ' + period + '.';
    })();

    function injectGreeting() {
        if (document.getElementById('cl-greeting')) return;
        var ws = document.getElementById('welcome-screen');
        if (!ws) return;
        var img = ws.querySelector('img');
        if (!img) return;
        var el = document.createElement('p');
        el.id = 'cl-greeting';
        el.textContent = _greetingText;
        el.style.cssText = 'font-size:18px;font-weight:500;color:#475569;margin:0 0 8px 0;text-align:center;font-family:Inter,sans-serif;width:100%;';
        img.insertAdjacentElement('afterend', el);
    }
    injectGreeting();
    setTimeout(injectGreeting, 500);
    setTimeout(injectGreeting, 1500);

    function setPlaceholder() {
        var el = document.querySelector('textarea');
        if (el) {
            el.placeholder = 'Enter a condition, drug name, NCT ID, or research question…';
            return;
        }
        var ce = document.querySelector('[contenteditable="true"]');
        if (ce) ce.setAttribute('data-placeholder', 'Enter a condition, drug name, NCT ID, or research question…');
    }
    setPlaceholder();
    setTimeout(setPlaceholder, 1000);
    setTimeout(setPlaceholder, 3000);

    function injectDataSourceBadge() {
        var header = document.getElementById('header');
        if (!header || document.getElementById('cl-datasource-badge')) return;
        var badge = document.createElement('div');
        badge.id = 'cl-datasource-badge';
        badge.innerHTML = '<span>🏥 ClinicalTrials.gov</span><span class="cl-dot"> · </span><span>📚 PubMed</span>';
        header.appendChild(badge);
    }
    injectDataSourceBadge();
    setTimeout(injectDataSourceBadge, 500);
    setTimeout(injectDataSourceBadge, 2000);

    var uCount = 0, aCount = 0;
    new MutationObserver(function () {
        injectGreeting();
        injectDataSourceBadge();
        hideThemeToggle();
        setPlaceholder();
        var u = document.querySelectorAll('[class*="user-message"], [class*="UserMessage"]').length;
        var a = document.querySelectorAll('[class*="assistant-message"], [class*="AssistantMessage"]').length;
        if (u > uCount) { playSend(); uCount = u; }
        if (a > aCount) { setTimeout(function () { playDone(); aCount = a; }, 800); }
    }).observe(document.body, { childList: true, subtree: true });
})();
