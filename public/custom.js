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

    var uCount = 0, aCount = 0;
    new MutationObserver(function () {
        var u = document.querySelectorAll('[class*="user-message"], [class*="UserMessage"]').length;
        var a = document.querySelectorAll('[class*="assistant-message"], [class*="AssistantMessage"]').length;
        if (u > uCount) { playSend(); uCount = u; }
        if (a > aCount) { setTimeout(function () { playDone(); aCount = a; }, 800); }
    }).observe(document.body, { childList: true, subtree: true });
})();
