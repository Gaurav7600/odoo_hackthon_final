/** @odoo-module **/
/**
 * DO SIGNUP APPROVAL — Advanced Auth Page Animations
 * Particle canvas, form interactivity, loading states
 */

(function () {
    "use strict";

    /* ── Guard: only run on our custom auth pages ─────────────────────────── */
    function isAuthPage() {
        return document.body.classList.contains("o_auth_page");
    }

    /* ── 1. PARTICLE CANVAS ────────────────────────────────────────────────── */
    function initParticles() {
        const canvas = document.getElementById("do-particle-canvas");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        let W = (canvas.width = window.innerWidth);
        let H = (canvas.height = window.innerHeight);

        const COLORS = ["#7c3aed", "#4f46e5", "#06b6d4", "#0284c7", "#a78bfa"];
        const NUM = Math.min(60, Math.floor((W * H) / 20000));

        const particles = Array.from({ length: NUM }, () => ({
            x: Math.random() * W,
            y: Math.random() * H,
            r: Math.random() * 2 + 0.5,
            dx: (Math.random() - 0.5) * 0.4,
            dy: (Math.random() - 0.5) * 0.4,
            color: COLORS[Math.floor(Math.random() * COLORS.length)],
            alpha: Math.random() * 0.5 + 0.1,
            pulse: Math.random() * Math.PI * 2,
        }));

        /* Connect nearby particles with lines */
        function drawConnections() {
            const threshold = 120;
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < threshold) {
                        const alpha = ((threshold - dist) / threshold) * 0.12;
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(124,58,237,${alpha})`;
                        ctx.lineWidth = 0.8;
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }
        }

        let frame = 0;
        function animate() {
            ctx.clearRect(0, 0, W, H);
            frame++;

            drawConnections();

            particles.forEach((p) => {
                p.pulse += 0.015;
                const alpha = p.alpha + Math.sin(p.pulse) * 0.08;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r + Math.sin(p.pulse) * 0.4, 0, Math.PI * 2);
                ctx.fillStyle =
                    p.color +
                    Math.round(Math.max(0, Math.min(255, alpha * 255)))
                        .toString(16)
                        .padStart(2, "0");
                ctx.fill();

                p.x += p.dx;
                p.y += p.dy;

                if (p.x < 0 || p.x > W) p.dx *= -1;
                if (p.y < 0 || p.y > H) p.dy *= -1;
            });

            requestAnimationFrame(animate);
        }

        animate();

        window.addEventListener("resize", () => {
            W = canvas.width = window.innerWidth;
            H = canvas.height = window.innerHeight;
        });
    }

    /* ── 2. MOUSE PARALLAX on the card ────────────────────────────────────── */
    function initParallax() {
        const card = document.querySelector(".do-auth-card");
        if (!card) return;

        document.addEventListener("mousemove", (e) => {
            const cx = window.innerWidth / 2;
            const cy = window.innerHeight / 2;
            const rx = ((e.clientY - cy) / cy) * -4;
            const ry = ((e.clientX - cx) / cx) * 4;
            card.style.transform = `perspective(1000px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(0)`;
        });

        document.addEventListener("mouseleave", () => {
            card.style.transform =
                "perspective(1000px) rotateX(0deg) rotateY(0deg)";
        });

        /* Smooth transition on card itself */
        card.style.transition =
            "transform 0.15s ease, box-shadow 0.3s ease, opacity 0.7s ease";
    }

    /* ── 3. FORM SUBMIT LOADING STATE ────────────────────────────────────── */
    function initFormLoading() {
        const forms = document.querySelectorAll(".do-auth-form");
        forms.forEach((form) => {
            form.addEventListener("submit", () => {
                const btn = form.querySelector(".do-auth-btn");
                if (btn) btn.classList.add("loading");
            });
        });
    }

    /* ── 4. INPUT FLOATING LABEL EFFECT (aria + visual) ─────────────────── */
    function initInputEffects() {
        const inputs = document.querySelectorAll(".do-auth-form input");
        inputs.forEach((input) => {
            if (input.value) input.closest(".do-input-group") &&
                input.closest(".do-input-group").classList.add("has-value");

            input.addEventListener("input", () => {
                const group = input.closest(".do-input-group");
                if (group) group.classList.toggle("has-value", input.value.length > 0);
            });
        });
    }

    /* ── 5. ANIMATED COUNTER (for waiting page) ──────────────────────────── */
    function initWaitingDots() {
        const el = document.querySelector(".do-waiting-dots");
        if (!el) return;
        let dots = 0;
        setInterval(() => {
            dots = (dots + 1) % 4;
            el.textContent = ".".repeat(dots);
        }, 500);
    }

    /* ── 6. PASSWORD TOGGLE ──────────────────────────────────────────────── */
    function initPasswordToggle() {
        document.querySelectorAll(".do-pw-toggle").forEach((btn) => {
            btn.addEventListener("click", () => {
                const input = btn.closest(".do-input-group").querySelector("input");
                if (!input) return;
                const isPassword = input.type === "password";
                input.type = isPassword ? "text" : "password";
                const icon = btn.querySelector("i");
                if (icon) {
                    icon.classList.toggle("fa-eye", !isPassword);
                    icon.classList.toggle("fa-eye-slash", isPassword);
                }
            });
        });
    }

    /* ── 7. TYPEWRITER EFFECT on heading ─────────────────────────────────── */
    function initTypewriter() {
        const el = document.querySelector("[data-typewriter]");
        if (!el) return;
        const text = el.dataset.typewriter;
        el.textContent = "";
        let i = 0;
        const interval = setInterval(() => {
            if (i >= text.length) { clearInterval(interval); return; }
            el.textContent += text[i++];
        }, 60);
    }

    /* ── BOOT ────────────────────────────────────────────────────────────── */
    function boot() {
        if (!isAuthPage()) return;
        initParticles();
        initParallax();
        initFormLoading();
        initInputEffects();
        initWaitingDots();
        initPasswordToggle();
        initTypewriter();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
