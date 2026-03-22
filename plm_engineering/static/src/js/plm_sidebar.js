/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

export class PlmSidebar extends Component {
    static template = "plm_engineering.PlmSidebar";
    static props = {};

    setup() {
        this.action = useService("action");
        this.menu   = useService("menu");
        this.orm    = useService("orm");

        try { this.companyService = useService("company"); }
        catch (_) { this.companyService = null; }

        this.state = useState({
            collapsed: false, mobileOpen: false, activeMenuId: null,
            expanded: {}, menus: [], profileOpen: false,
            userName: "", userEmail: "", userInitials: "",
            userId: null,
            userAvatarB64: "",
            companyName: "",
            allCompanies: [], activeCompanyIds: [],
        });

        this._onKeyDown  = (e) => {
            if (e.key === "Escape") {
                this.state.mobileOpen  = false;
                this.state.profileOpen = false;
            }
        };
        this._onResize = () => {
            if (window.innerWidth < 992) {
                document.body.classList.remove("plm-collapsed");
                document.body.classList.add("plm-mobile");
            } else {
                document.body.classList.remove("plm-mobile");
                document.body.classList.toggle("plm-collapsed", this.state.collapsed);
            }
        };
        this._onDocClick = (e) => {
            if (this.state.profileOpen && !e.target.closest(".plm-user-wrap"))
                this.state.profileOpen = false;
        };

        onMounted(async () => {
            document.addEventListener("keydown", this._onKeyDown);
            document.addEventListener("click",   this._onDocClick);
            window.addEventListener("resize",    this._onResize);
            this._injectCSS();
            this._injectMobileBtn();
            this._hideNavbar();
            this._onResize();
            this._syncActiveMenu();
            this._loadMenus();
            await this._loadUserInfo();
            this._menuPollTimer = setInterval(() => {
                const m = this._fetchTopMenus();
                if (m.length > 0) {
                    this.state.menus = m;
                    clearInterval(this._menuPollTimer);
                    this._menuPollTimer = null;
                }
            }, 120);
            setTimeout(() => {
                if (this._menuPollTimer) {
                    clearInterval(this._menuPollTimer);
                    this._menuPollTimer = null;
                }
            }, 5000);
        });

        onWillUnmount(() => {
            document.removeEventListener("keydown", this._onKeyDown);
            document.removeEventListener("click",   this._onDocClick);
            window.removeEventListener("resize",    this._onResize);
            if (this._menuPollTimer) clearInterval(this._menuPollTimer);
            document.getElementById("plm-mobile-btn")?.remove();
            ["plm-css", "plm-navbar-css"].forEach(id => document.getElementById(id)?.remove());
            document.body.classList.remove("plm-collapsed", "plm-mobile");
        });
    }

    async _loadUserInfo() {
        try {
            // ── Step 1: Get real session uid from server
            let uid = null;
            let name = "", login = "", companyName = "", partnerId = null;

            try {
                const resp = await fetch("/web/dataset/call_kw", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        jsonrpc: "2.0", id: 1, method: "call",
                        params: {
                            model: "res.users", method: "read",
                            args: [[session.uid], ["id", "name", "login", "company_id", "partner_id", "share"]],
                            kwargs: { context: session.user_context || {} },
                        },
                    }),
                });
                const j = await resp.json();
                if (j.result?.length) {
                    const u = j.result[0];
                    if (u.name !== "OdooBot" && u.name !== "__system__") {
                        uid        = u.id;
                        name       = u.name;
                        login      = u.login;
                        companyName = Array.isArray(u.company_id) ? u.company_id[1] : "";
                        partnerId  = Array.isArray(u.partner_id)  ? u.partner_id[0] : null;
                    }
                }
            } catch (_) {}

            // ── Step 2: Fallback to get_session_info if needed
            if (!uid) {
                try {
                    const r2 = await fetch("/web/session/get_session_info", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "call", params: {} }),
                    });
                    const j2 = await r2.json();
                    if (j2.result) {
                        uid        = j2.result.uid;
                        name       = j2.result.name;
                        login      = j2.result.username;
                        companyName = j2.result.company_name || "";
                        partnerId  = j2.result.partner_id   || null;
                    }
                } catch (_) {}
            }

            // ── Step 3: Final fallback to session object
            if (!uid) {
                uid        = session.uid;
                name       = session.name       || "User";
                login      = session.username   || "";
                companyName = session.company_name || "";
            }

            this.state.userId      = uid;
            this.state.userName    = name;
            this.state.userEmail   = login;
            this.state.companyName = companyName;
            this._buildInitials();

            // ── Step 4: Load avatar image as BASE64 via ORM
            await this._loadAvatarBase64(uid, partnerId);

        } catch (e) {
            console.warn("[PLM] _loadUserInfo error:", e);
            this.state.userId       = session.uid || null;
            this.state.userName     = session.name || "User";
            this.state.userEmail    = session.username || "";
            this.state.userInitials = this._initialsFromName(session.name || "AD");
            this.state.userAvatarB64 = "";
            if (session.uid) {
                await this._loadAvatarBase64(session.uid, null).catch(() => {});
            }
        }
    }

    async _loadAvatarBase64(userId, partnerId) {
        // Try 1: Read image_128 from res.partner (most reliable in Odoo 18)
        if (partnerId) {
            try {
                const rows = await this.orm.read(
                    "res.partner", [partnerId], ["image_128"]
                );
                const b64 = rows?.[0]?.image_128;
                if (b64 && b64 !== false && b64.length > 100) {
                    this.state.userAvatarB64 = b64;
                    return;
                }
            } catch (_) {}
        }

        // Try 2: Read image_128 from res.users
        if (userId) {
            try {
                const rows = await this.orm.read(
                    "res.users", [userId], ["image_128"]
                );
                const b64 = rows?.[0]?.image_128;
                if (b64 && b64 !== false && b64.length > 100) {
                    this.state.userAvatarB64 = b64;
                    return;
                }
            } catch (_) {}
        }

        // Try 3: Read avatar_128 from res.users (computed field)
        if (userId) {
            try {
                const rows = await this.orm.read(
                    "res.users", [userId], ["avatar_128"]
                );
                const b64 = rows?.[0]?.avatar_128;
                if (b64 && b64 !== false && b64.length > 100) {
                    this.state.userAvatarB64 = b64;
                    return;
                }
            } catch (_) {}
        }

        // No image found — initials will show
        this.state.userAvatarB64 = "";
    }

    // ── Getter: build data: URL from base64 string
    getUserAvatar() {
        const b64 = this.state.userAvatarB64;
        if (!b64) return "";
        const mime = b64.startsWith("/9j/") ? "image/jpeg" : "image/png";
        return `data:${mime};base64,${b64}`;
    }

    _buildInitials() {
        this.state.userInitials = this._initialsFromName(this.state.userName);
    }

    _initialsFromName(name) {
        const parts = (name || "").trim().split(/\s+/).filter(Boolean);
        if (parts.length >= 2)  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return "AD";
    }

    //  GETTERS
    getUserName()       { return this.state.userName     || ""; }
    getUserEmail()      { return this.state.userEmail     || ""; }
    getUserId()         { return this.state.userId        || session.uid || null; }
    getUserInitials()   { return this.state.userInitials  || "AD"; }
    getCompanyName()    { return this.state.companyName   || ""; }
    hasAvatar()         { return !!this.state.userAvatarB64; }
    isProfileOpen()     { return this.state.profileOpen; }
    isCompanyActive(id) { return (this.state.activeCompanyIds || []).includes(id); }

    //  PROFILE ACTIONS
    toggleProfileDropdown() { this.state.profileOpen = !this.state.profileOpen; }

    async openPreferences() {
        this.state.profileOpen = false;
        const uid = this.getUserId();
        try {
            await this.action.doAction({
                type: "ir.actions.act_window", res_model: "res.users", res_id: uid,
                name: "My Preferences", views: [[false, "form"]], target: "new",
                context: { form_view_ref: "base.res_users_preferences_form_view" },
            });
        } catch (_) {
            try { await this.action.doAction("base.action_res_users_my"); }
            catch (_2) {
                try { await this.action.doAction({ type: "ir.actions.act_window", res_model: "res.users", res_id: uid, views: [[false, "form"]], target: "new" }); }
                catch (e) { console.warn("[PLM] prefs:", e); }
            }
        }
    }

    async openNotifications() {
        this.state.profileOpen = false;
        try { await this.action.doAction({ type: "ir.actions.client", tag: "mail.action_discuss", target: "current" }); } catch (_) {}
    }

    async toggleCompany(companyId) {
        try {
            const cs = this.companyService;
            let ids = [...(this.state.activeCompanyIds || [])];
            const idx = ids.indexOf(companyId);
            if (idx >= 0) { if (ids.length <= 1) return; ids.splice(idx, 1); } else { ids.push(companyId); }
            this.state.activeCompanyIds = [...ids];
            if (cs && typeof cs.setCompanies === "function") { await cs.setCompanies(ids); }
            else { const u = new URL(browser.location.href); u.searchParams.set("cids", ids.join("-")); browser.location.assign(u.toString()); }
        } catch (e) { console.warn("[PLM] toggleCompany:", e); }
    }

    //  MENU HELPERS
    _fetchTopMenus() {
        try { const a = this.menu.getCurrentApp(); if (!a) return []; return this.menu.getMenuAsTree(a.id)?.childrenTree || []; }
        catch (_) { return []; }
    }
    _loadMenus()        { this.state.menus = this._fetchTopMenus(); }
    getTopMenus()       { return this.state.menus; }
    getChildren(n)      { return n?.childrenTree || []; }
    hasChildren(n)      { return (n?.childrenTree || []).length > 0; }
    getCurrentApp()     { return this.menu.getCurrentApp(); }
    getAllApps()         { return this.menu.getApps(); }
    _syncActiveMenu()   { const c = this.menu.getCurrentApp(); if (c) this.state.activeMenuId = c.id; }

    async onMenuClick(n)    { this.hasChildren(n) ? this.toggleSection(n.id) : await this._doNavigate(n); }
    async onSubMenuClick(n) { await this._doNavigate(n); }
    async _doNavigate(node) {
        this.state.activeMenuId = node.id;
        if (window.innerWidth < 992) this.state.mobileOpen = false;
        try { await this.menu.selectMenu(node); this._loadMenus(); } catch (e) { console.warn("[PLM] nav:", e); }
    }
    async switchApp(app) {
        this.state.activeMenuId = app.id;
        if (window.innerWidth < 992) this.state.mobileOpen = false;
        try { await this.menu.selectMenu(app); this._loadMenus(); setTimeout(() => this._loadMenus(), 300); } catch (e) { console.warn("[PLM] app:", e); }
    }
    async logout() { browser.location.href = "/web/session/logout?redirect=/web/login"; }

    toggleSection(id) { this.state.expanded[id] = !this.state.expanded[id]; }
    expand()   { this.state.collapsed = false; document.body.classList.remove("plm-collapsed"); }
    collapse() { this.state.collapsed = true;  document.body.classList.add("plm-collapsed"); }
    closeMobile()     { this.state.mobileOpen = false; }
    isActive(id)      { return this.state.activeMenuId === id; }
    isSectionOpen(id) { return !!this.state.expanded[id]; }
    isMobileOpen()    { return this.state.mobileOpen; }
    isCollapsed()     { return this.state.collapsed; }

    getMenuIcon(node) {
        if (node.web_icon) { const p = node.web_icon.split(","); if (p[0]?.startsWith("fa")) return p[0]; }
        const n = (node.name || "").toLowerCase();
        if (n.includes("dashboard"))                         return "fa fa-th-large";
        if (n.includes("change order") || n.includes("eco"))return "fa fa-random";
        if (n.includes("product"))                           return "fa fa-cube";
        if (n.includes("bom") || n.includes("bill"))         return "fa fa-file-text-o";
        if (n.includes("report") || n.includes("analysis"))  return "fa fa-bar-chart";
        if (n.includes("setting") || n.includes("config"))   return "fa fa-cog";
        if (n.includes("master"))                            return "fa fa-database";
        if (n.includes("user") || n.includes("team"))        return "fa fa-users";
        if (n.includes("order") || n.includes("purchase"))   return "fa fa-shopping-cart";
        if (n.includes("invoice") || n.includes("account"))  return "fa fa-file-text";
        if (n.includes("inventory") || n.includes("stock"))  return "fa fa-cubes";
        if (n.includes("manufacture"))                       return "fa fa-industry";
        if (n.includes("project"))                           return "fa fa-tasks";
        if (n.includes("sale"))                              return "fa fa-dollar";
        if (n.includes("crm"))                               return "fa fa-phone";
        if (n.includes("hr") || n.includes("employee"))      return "fa fa-id-badge";
        if (n.includes("discuss"))                           return "fa fa-comment-o";
        if (n.includes("apps"))                              return "fa fa-th";
        return "fa fa-circle-o";
    }

    _hideNavbar() {
        if (document.getElementById("plm-navbar-css")) return;
        const s = document.createElement("style");
        s.id = "plm-navbar-css";
        s.textContent = `
            .o_main_navbar { display:none !important; }
            .o_web_client  { padding-top:0 !important; }
            .o_action_manager,
            .o_main_components_container {
                margin-left:240px;
                transition:margin-left 0.25s cubic-bezier(.4,0,.2,1);
            }
            body.plm-collapsed .o_action_manager,
            body.plm-collapsed .o_main_components_container { margin-left:60px; }
            body.plm-mobile   .o_action_manager,
            body.plm-mobile   .o_main_components_container  { margin-left:0; }
        `;
        document.head.appendChild(s);
    }

    _injectCSS() {
        if (document.getElementById("plm-css")) return;
        const s = document.createElement("style");
        s.id = "plm-css";
        s.textContent = `
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&display=swap');
:root{
    --plm-bg:#0f1923;--plm-bg2:#162032;--plm-bg3:#1c2b3a;--plm-bg4:#1a2535;
    --plm-dd:#192436;--plm-border:rgba(255,255,255,0.07);
    --plm-text:#c9d1d9;--plm-muted:#5a6a7a;
    --plm-cyan:#29b6f6;--plm-cyan2:#1a8fe3;
    --plm-green:#3fb950;--plm-red:#f85149;
    --plm-act-bg:rgba(41,182,246,0.12);--plm-act-bd:rgba(41,182,246,0.25);
    --plm-w:240px;--plm-wc:60px;
    --plm-ease:0.25s cubic-bezier(.4,0,.2,1);
    --plm-font:'Sora',system-ui,sans-serif;
}
.plm-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.55);backdrop-filter:blur(3px);z-index:1045}
.plm-backdrop.on{display:block}
.plm-sb{position:fixed;top:0;left:0;bottom:0;width:var(--plm-w);background:var(--plm-bg);border-right:1px solid var(--plm-border);display:flex;flex-direction:column;z-index:1050;font-family:var(--plm-font);transition:width var(--plm-ease),transform var(--plm-ease);overflow:hidden}
body.plm-collapsed .plm-sb{width:var(--plm-wc)}
@media(max-width:991px){.plm-sb{transform:translateX(-100%);width:var(--plm-w)!important;box-shadow:8px 0 40px rgba(0,0,0,.65)}.plm-sb.mob-open{transform:translateX(0)}}
.plm-hdr{display:flex;align-items:center;gap:10px;padding:0 12px;height:58px;flex-shrink:0;border-bottom:1px solid var(--plm-border);overflow:hidden}
.plm-logo{width:32px;height:32px;flex-shrink:0;border-radius:8px;background:linear-gradient(135deg,var(--plm-cyan),var(--plm-cyan2));display:flex;align-items:center;justify-content:center;box-shadow:0 0 12px rgba(41,182,246,.3);cursor:pointer}
.plm-logo i{color:#fff;font-size:14px}.plm-logo img{width:17px;height:17px;object-fit:contain;filter:brightness(10)}
.plm-brand{flex:1;overflow:hidden;min-width:0}
.plm-brand-n{display:block;font-size:13px;font-weight:600;color:var(--plm-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.plm-cbtn{width:26px;height:26px;flex-shrink:0;border-radius:6px;border:1px solid var(--plm-border);background:var(--plm-bg3);color:var(--plm-muted);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .2s}
.plm-cbtn:hover{background:var(--plm-bg2);color:var(--plm-text)}.plm-cbtn i{font-size:11px}
body.plm-collapsed .plm-sb .plm-brand,body.plm-collapsed .plm-sb .plm-cbtn{display:none}
.plm-expand-btn{display:none;width:100%;padding:8px 0;align-items:center;justify-content:center;cursor:pointer;border:none;background:transparent;color:var(--plm-muted);border-bottom:1px solid var(--plm-border);transition:background .2s,color .2s;flex-shrink:0}
.plm-expand-btn:hover{background:var(--plm-bg2);color:var(--plm-text)}.plm-expand-btn i{font-size:13px}
body.plm-collapsed .plm-sb .plm-expand-btn{display:flex}
.plm-nav{flex:1;overflow-y:auto;overflow-x:hidden;padding:6px 0;scrollbar-width:thin;scrollbar-color:rgba(255,255,255,0.06) transparent}
.plm-nav::-webkit-scrollbar{width:3px}.plm-nav::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.08);border-radius:3px}
.plm-lbl{padding:12px 14px 4px;font-size:9.5px;font-weight:600;letter-spacing:1.1px;text-transform:uppercase;color:var(--plm-muted);white-space:nowrap;overflow:hidden;transition:opacity var(--plm-ease),height var(--plm-ease),padding var(--plm-ease)}
body.plm-collapsed .plm-sb .plm-lbl{opacity:0;height:0;padding:0;pointer-events:none}
.plm-ni{display:flex;align-items:center;gap:10px;padding:7px 10px;cursor:pointer;color:var(--plm-text);position:relative;margin:1px 6px;border-radius:7px;white-space:nowrap;user-select:none;border:1px solid transparent;transition:background .15s,color .15s,border-color .15s}
.plm-ni:hover{background:var(--plm-bg2)}.plm-ni--on{background:var(--plm-act-bg)!important;border-color:var(--plm-act-bd)!important;color:var(--plm-text)!important}
body.plm-collapsed .plm-sb .plm-ni{justify-content:center;padding:9px 0}
.plm-iw{width:30px;height:30px;flex-shrink:0;border-radius:7px;background:var(--plm-bg3);display:flex;align-items:center;justify-content:center;transition:background .2s,box-shadow .2s}
.plm-ni:hover .plm-iw{background:var(--plm-bg4)}.plm-ni--on .plm-iw{background:var(--plm-cyan2);box-shadow:0 2px 8px rgba(26,143,227,.4)}
.plm-iw i{font-size:13px;color:var(--plm-muted);transition:color .2s}.plm-ni:hover .plm-iw i{color:var(--plm-text)}.plm-ni--on .plm-iw i{color:#fff}
.plm-iw img{width:15px;height:15px;object-fit:contain;filter:brightness(0) invert(0.55)}.plm-ni--on .plm-iw img{filter:brightness(0) invert(1)}
.plm-nl{flex:1;font-size:13px;font-weight:500;overflow:hidden;text-overflow:ellipsis}
.plm-ch{font-size:9px;color:var(--plm-muted);flex-shrink:0;transition:transform var(--plm-ease)}.plm-ch--o{transform:rotate(90deg)}
body.plm-collapsed .plm-sb .plm-nl,body.plm-collapsed .plm-sb .plm-ch{display:none}
body.plm-collapsed .plm-sb .plm-ni:hover::after{content:attr(data-tip);position:absolute;left:calc(100% + 10px);top:50%;transform:translateY(-50%);background:var(--plm-bg3);color:var(--plm-text);font-size:12px;padding:6px 10px;border-radius:7px;white-space:nowrap;border:1px solid var(--plm-border);box-shadow:0 4px 20px rgba(0,0,0,.5);z-index:9999;pointer-events:none;font-family:var(--plm-font)}
.plm-sg{overflow:hidden;animation:sgIn .18s ease}
@keyframes sgIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
body.plm-collapsed .plm-sb .plm-sg{display:none}
.plm-si{display:flex;align-items:center;gap:8px;padding:6px 10px 6px 50px;border-radius:6px;cursor:pointer;font-size:12.5px;color:var(--plm-muted);margin:1px 6px;transition:background .15s,color .15s;user-select:none;white-space:nowrap}
.plm-si:hover{background:var(--plm-bg2);color:var(--plm-text)}.plm-si--on{color:var(--plm-cyan)!important;background:rgba(41,182,246,.07);font-weight:500}
.plm-dot{width:4px;height:4px;border-radius:50%;background:var(--plm-muted);flex-shrink:0;transition:background .15s}
.plm-si:hover .plm-dot,.plm-si--on .plm-dot{background:var(--plm-cyan)}
.plm-ssi{display:flex;align-items:center;gap:8px;padding:5px 10px 5px 66px;border-radius:6px;cursor:pointer;font-size:12px;color:var(--plm-muted);margin:1px 6px;transition:background .15s,color .15s;user-select:none;white-space:nowrap}
.plm-ssi:hover{background:var(--plm-bg2);color:var(--plm-text)}.plm-ssi--on{color:var(--plm-cyan)!important;background:rgba(41,182,246,.05);font-weight:500}
.plm-ssi-dot{width:3px;height:3px;border-radius:50%;background:var(--plm-muted);flex-shrink:0;transition:background .15s}
.plm-ssi:hover .plm-ssi-dot,.plm-ssi--on .plm-ssi-dot{background:var(--plm-cyan)}
.plm-divider{height:1px;background:var(--plm-border);margin:6px 12px}
.plm-user-wrap{position:relative;flex-shrink:0;border-top:1px solid var(--plm-border)}
.plm-user{display:flex;align-items:center;gap:10px;padding:10px 12px;cursor:pointer;transition:background .15s;overflow:hidden}
.plm-user:hover{background:rgba(41,182,246,0.05)}

.plm-user-av{
    width:36px;height:36px;flex-shrink:0;border-radius:50%;
    overflow:hidden;position:relative;
    background:linear-gradient(135deg,#1e4d8c,#0d2d5e);
    display:flex;align-items:center;justify-content:center;
    border:2px solid rgba(41,182,246,0.4);
}
.plm-av-initials{
    position:absolute;inset:0;z-index:1;
    display:flex;align-items:center;justify-content:center;
    font-size:13px;font-weight:700;color:#fff;
    text-transform:uppercase;user-select:none;pointer-events:none;
}
.plm-av-photo{
    position:absolute;inset:0;z-index:2;
    width:100%;height:100%;
    object-fit:cover;border-radius:50%;
    display:block;
}
.plm-av-dot{
    position:absolute;bottom:1px;right:1px;z-index:3;
    width:9px;height:9px;border-radius:50%;
    background:var(--plm-green);border:2px solid var(--plm-bg);
}

.plm-user-info{flex:1;overflow:hidden;min-width:0}
.plm-user-name{display:block;font-size:12.5px;font-weight:600;color:var(--plm-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.35}
.plm-user-email{display:block;font-size:10.5px;color:var(--plm-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px;line-height:1.35}
.plm-user-caret{font-size:10px;color:var(--plm-muted);flex-shrink:0;transition:transform var(--plm-ease)}
.plm-user-caret.open{transform:rotate(180deg)}
body.plm-collapsed .plm-sb .plm-user-info,body.plm-collapsed .plm-sb .plm-user-caret{display:none}
body.plm-collapsed .plm-sb .plm-user{justify-content:center;padding:10px 0}

.plm-profile-dd{display:none;position:absolute;bottom:calc(100% + 6px);left:8px;right:8px;background:var(--plm-dd);border:1px solid rgba(41,182,246,0.2);border-radius:12px;overflow:hidden;box-shadow:0 -16px 56px rgba(0,0,0,.8);z-index:2000;animation:ddUp .18s ease}
.plm-profile-dd.open{display:block}
@keyframes ddUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.plm-dd-hdr{display:flex;align-items:center;gap:12px;padding:14px 14px 12px;background:rgba(41,182,246,0.06);border-bottom:1px solid rgba(255,255,255,0.06)}

.plm-dd-av{
    width:46px;height:46px;flex-shrink:0;border-radius:50%;
    overflow:hidden;position:relative;
    background:linear-gradient(135deg,#1e4d8c,#0d2d5e);
    display:flex;align-items:center;justify-content:center;
    border:2px solid rgba(41,182,246,0.45);
}
.plm-dd-av-initials{
    position:absolute;inset:0;z-index:1;
    display:flex;align-items:center;justify-content:center;
    font-size:16px;font-weight:700;color:#fff;
    text-transform:uppercase;user-select:none;pointer-events:none;
}
.plm-dd-av-photo{
    position:absolute;inset:0;z-index:2;
    width:100%;height:100%;
    object-fit:cover;border-radius:50%;
    display:block;
}

.plm-dd-info{flex:1;overflow:hidden}
.plm-dd-name{font-size:13.5px;font-weight:600;color:var(--plm-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.3}
.plm-dd-email{font-size:11px;color:var(--plm-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}
.plm-dd-co{font-size:10.5px;color:var(--plm-cyan);margin-top:5px;display:flex;align-items:center;gap:4px;opacity:.9}
.plm-dd-co i{font-size:9px}
.plm-dd-menu{padding:5px 0}
.plm-dd-item{display:flex;align-items:center;gap:12px;padding:10px 16px;cursor:pointer;color:var(--plm-text);font-size:13px;font-family:var(--plm-font);font-weight:400;transition:background .15s;border:none;background:none;width:100%;text-align:left}
.plm-dd-item:hover{background:rgba(41,182,246,0.07);color:#fff}
.plm-dd-item i{width:16px;text-align:center;font-size:14px;color:var(--plm-muted);flex-shrink:0;transition:color .15s}
.plm-dd-item:hover i{color:var(--plm-cyan)}
.plm-dd-sep{height:1px;background:rgba(255,255,255,0.07);margin:3px 0}
.plm-dd-item.danger{color:var(--plm-red)!important}.plm-dd-item.danger i{color:var(--plm-red)!important}
.plm-dd-item.danger:hover{background:rgba(248,81,73,0.09)!important}
.plm-co-wrap{border-top:1px solid rgba(255,255,255,0.07);display:flex;flex-direction:column;max-height:190px}
.plm-co-title{padding:9px 15px 5px;font-size:9.5px;font-weight:600;letter-spacing:1.1px;text-transform:uppercase;color:var(--plm-muted);flex-shrink:0}
.plm-co-list{flex:1;overflow-y:auto;overflow-x:hidden;padding:0 0 6px;scrollbar-width:thin;scrollbar-color:rgba(41,182,246,0.25) transparent}
.plm-co-list::-webkit-scrollbar{width:4px}.plm-co-list::-webkit-scrollbar-thumb{background:rgba(41,182,246,0.3);border-radius:4px}
.plm-co-item{display:flex;align-items:center;gap:9px;padding:7px 14px;cursor:pointer;transition:background .15s;min-height:36px}
.plm-co-item:hover{background:rgba(41,182,246,0.07)}
.plm-co-cb{width:15px;height:15px;min-width:15px;border-radius:3px;border:1.5px solid var(--plm-muted);display:flex;align-items:center;justify-content:center;transition:all .15s;flex-shrink:0}
.plm-co-cb.on{background:var(--plm-cyan2);border-color:var(--plm-cyan2)}
.plm-co-cb.on::after{content:'';display:block;width:8px;height:5px;border-left:2px solid #fff;border-bottom:2px solid #fff;transform:rotate(-45deg) translateY(-1px)}
.plm-co-ico{width:24px;height:24px;min-width:24px;border-radius:5px;background:rgba(41,182,246,0.1);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.plm-co-ico i{font-size:11px;color:var(--plm-cyan)}
.plm-co-name{flex:1;font-size:12px;color:var(--plm-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.3}
.plm-co-name.active-co{color:var(--plm-cyan);font-weight:600}
.plm-logout{display:flex;align-items:center;gap:9px;padding:9px 14px 12px;cursor:pointer;color:var(--plm-red);font-size:13px;font-family:var(--plm-font);font-weight:500;flex-shrink:0;white-space:nowrap;overflow:hidden;background:none;border:none;border-top:1px solid var(--plm-border);transition:color .15s,background .15s;width:100%}
.plm-logout:hover{color:#ff6b64;background:rgba(248,81,73,0.05)}
.plm-logout i{font-size:14px;flex-shrink:0}.plm-logout-txt{overflow:hidden;text-overflow:ellipsis}
body.plm-collapsed .plm-sb .plm-logout{justify-content:center;padding:10px 0 12px}
body.plm-collapsed .plm-sb .plm-logout-txt{display:none}
body.plm-collapsed .plm-sb .plm-logout:hover::after{content:'Log Out';position:absolute;left:calc(100% + 10px);top:50%;transform:translateY(-50%);background:var(--plm-bg3);color:var(--plm-red);font-size:12px;padding:6px 10px;border-radius:7px;white-space:nowrap;border:1px solid rgba(248,81,73,.2);box-shadow:0 4px 20px rgba(0,0,0,.5);z-index:9999;pointer-events:none}
.plm-burger{display:none;position:fixed;top:14px;left:14px;z-index:1055;width:36px;height:36px;border-radius:8px;border:1px solid var(--plm-border);background:var(--plm-bg2);cursor:pointer;flex-direction:column;align-items:center;justify-content:center;gap:5px;box-shadow:0 4px 16px rgba(0,0,0,.4);transition:background .2s}
.plm-burger:hover{background:var(--plm-bg3)}.plm-bar{width:16px;height:2px;background:var(--plm-text);border-radius:2px}
@media(max-width:991px){.plm-burger{display:flex}}
        `;
        document.head.appendChild(s);
    }

    _injectMobileBtn() {
        if (document.getElementById("plm-mobile-btn")) return;
        const btn = document.createElement("button");
        btn.id = "plm-mobile-btn"; btn.className = "plm-burger";
        btn.innerHTML = `<span class="plm-bar"></span><span class="plm-bar"></span><span class="plm-bar"></span>`;
        btn.addEventListener("click", () => { this.state.mobileOpen = true; });
        document.body.appendChild(btn);
    }
}

registry.category("main_components").add("PlmSidebar", { Component: PlmSidebar, props: {} });