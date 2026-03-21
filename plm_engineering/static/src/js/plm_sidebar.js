import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";

export class PlmSidebar extends Component {
    static template = "plm_engineering.PlmSidebar";
    static props = {};

    setup() {
        this.action = useService("action");
        this.menu   = useService("menu");

        this.state = useState({
            collapsed:    false,
            mobileOpen:   false,
            activeMenuId: null,
            expanded:     {},   // key = menu item id → true/false
            menus:        [],   // reactive cache of top-level menus for current app
        });

        this.onMenuClick      = this.onMenuClick.bind(this);
        this.onSubMenuClick   = this.onSubMenuClick.bind(this);
        this.toggleSection    = this.toggleSection.bind(this);
        this.collapse         = this.collapse.bind(this);
        this.expand           = this.expand.bind(this);
        this.closeMobile      = this.closeMobile.bind(this);
        this.isActive         = this.isActive.bind(this);
        this.isSectionOpen    = this.isSectionOpen.bind(this);
        this.isMobileOpen     = this.isMobileOpen.bind(this);
        this.isCollapsed      = this.isCollapsed.bind(this);
        this.getTopMenus      = this.getTopMenus.bind(this);
        this.getChildren      = this.getChildren.bind(this);
        this.hasChildren      = this.hasChildren.bind(this);
        this.logout           = this.logout.bind(this);

        this._onKeyDown = (e) => {
            if (e.key === "Escape" && this.state.mobileOpen) {
                this.state.mobileOpen = false;
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

        onMounted(() => {
            document.addEventListener("keydown", this._onKeyDown);
            window.addEventListener("resize", this._onResize);
            this._injectCSS();
            this._injectMobileBtn();
            this._hideNavbar();
            this._onResize();

            this._syncActiveMenu();
            this._loadMenus();

            this._menuPollTimer = setInterval(() => {
                const menus = this._fetchTopMenus();
                if (menus.length > 0) {
                    this.state.menus = menus;
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
            window.removeEventListener("resize", this._onResize);
            if (this._menuPollTimer) clearInterval(this._menuPollTimer);
            const btn = document.getElementById("plm-mobile-btn");
            if (btn) btn.remove();
            ["plm-css", "plm-navbar-css"].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.remove();
            });
            document.body.classList.remove("plm-collapsed", "plm-mobile");
        });
    }

    _fetchTopMenus() {
        try {
            const currentApp = this.menu.getCurrentApp();
            if (!currentApp) return [];
            const tree = this.menu.getMenuAsTree(currentApp.id);
            return tree?.childrenTree || [];
        } catch (_) {
            return [];
        }
    }

    _loadMenus() {
        const menus = this._fetchTopMenus();
        this.state.menus = menus;
    }

    getTopMenus() {
        return this.state.menus;
    }


    getChildren(menuNode) {
        return menuNode?.childrenTree || [];
    }

    hasChildren(menuNode) {
        return (menuNode?.childrenTree || []).length > 0;
    }

    getCurrentApp() {
        return this.menu.getCurrentApp();
    }


    getAllApps() {
        return this.menu.getApps();
    }

    _syncActiveMenu() {
        const current = this.menu.getCurrentApp();
        if (current) {
            this.state.activeMenuId = current.id;
        }
    }

    async onMenuClick(menuNode) {
        if (this.hasChildren(menuNode)) {
            this.toggleSection(menuNode.id);
        } else {
            await this._doNavigate(menuNode);
        }
    }

    async onSubMenuClick(menuNode) {
        await this._doNavigate(menuNode);
    }

    async _doNavigate(menuNode) {
        this.state.activeMenuId = menuNode.id;
        if (window.innerWidth < 992) this.state.mobileOpen = false;
        try {
            await this.menu.selectMenu(menuNode);
            this._loadMenus();
        } catch (e) {
            console.warn("[PLM Sidebar] Menu nav failed:", menuNode, e);
        }
    }

    async switchApp(app) {
        this.state.activeMenuId = app.id;
        if (window.innerWidth < 992) this.state.mobileOpen = false;
        try {
            await this.menu.selectMenu(app);
            this._loadMenus();
            setTimeout(() => this._loadMenus(), 300);
        } catch (e) {
            console.warn("[PLM Sidebar] App switch failed:", app, e);
        }
    }

    async logout() {
        browser.location.href = "/web/session/logout?redirect=/web/login";
    }

    toggleSection(id) {
        this.state.expanded[id] = !this.state.expanded[id];
    }

    expand() {
        this.state.collapsed = false;
        document.body.classList.remove("plm-collapsed");
    }

    collapse() {
        this.state.collapsed = true;
        document.body.classList.add("plm-collapsed");
    }

    closeMobile() {
        this.state.mobileOpen = false;
    }

    isActive(menuId)     { return this.state.activeMenuId === menuId; }
    isSectionOpen(id)    { return !!this.state.expanded[id]; }
    isMobileOpen()       { return this.state.mobileOpen; }
    isCollapsed()        { return this.state.collapsed; }

    getMenuIcon(menuNode) {
        if (menuNode.web_icon) {
            const parts = menuNode.web_icon.split(",");
            if (parts[0] && parts[0].startsWith("fa")) return parts[0];
        }
        const name = (menuNode.name || "").toLowerCase();
        if (name.includes("dashboard"))                      return "fa fa-tachometer";
        if (name.includes("change order") || name.includes("eco")) return "fa fa-file-text-o";
        if (name.includes("product"))                        return "fa fa-cube";
        if (name.includes("bom") || name.includes("bill"))  return "fa fa-sitemap";
        if (name.includes("report") || name.includes("analysis")) return "fa fa-bar-chart";
        if (name.includes("setting") || name.includes("config"))  return "fa fa-cog";
        if (name.includes("master"))                         return "fa fa-database";
        if (name.includes("user") || name.includes("team")) return "fa fa-users";
        if (name.includes("order") || name.includes("purchase"))  return "fa fa-shopping-cart";
        if (name.includes("invoice") || name.includes("account")) return "fa fa-file-text";
        if (name.includes("inventory") || name.includes("stock")) return "fa fa-cubes";
        if (name.includes("manufacture"))                    return "fa fa-industry";
        if (name.includes("project"))                        return "fa fa-tasks";
        if (name.includes("sale"))                           return "fa fa-dollar";
        if (name.includes("crm"))                            return "fa fa-phone";
        if (name.includes("hr") || name.includes("employee")) return "fa fa-id-badge";
        return "fa fa-circle-o";
    }

    // ── Odoo navbar hide ─────────────────────────────────────────────────────

    _hideNavbar() {
        if (document.getElementById("plm-navbar-css")) return;
        const s = document.createElement("style");
        s.id = "plm-navbar-css";
        s.textContent = `
            .o_main_navbar { display: none !important; }
            .o_web_client  { padding-top: 0 !important; }
            .o_action_manager,
            .o_main_components_container {
                margin-left: 260px;
                transition: margin-left 0.28s cubic-bezier(.4,0,.2,1);
            }
            body.plm-collapsed .o_action_manager,
            body.plm-collapsed .o_main_components_container { margin-left: 64px; }
            body.plm-mobile .o_action_manager,
            body.plm-mobile .o_main_components_container    { margin-left: 0; }
        `;
        document.head.appendChild(s);
    }

    // ── CSS ──────────────────────────────────────────────────────────────────

    _injectCSS() {
        if (document.getElementById("plm-css")) return;
        const s = document.createElement("style");
        s.id = "plm-css";
        s.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
            :root {
                --sb:linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%); --sb2:#161b22; --sb3:#21262d;
                --sbr:rgba(255,255,255,0.07);
                --st:#e6edf3; --sm:#7d8590;
                --sg:#3fb950; --sbl:#388bfd;
                --sr:#f85149; --sy:#d29922;
                --sw:260px; --swc:64px;
                --se:0.28s cubic-bezier(.4,0,.2,1);
                --sf:'Sora',system-ui,sans-serif;
                --smo:'JetBrains Mono',monospace;
            }

            /* Backdrop */
            .plm-backdrop { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.6); backdrop-filter:blur(3px); z-index:1045; }
            .plm-backdrop.on { display:block; }

            /* Sidebar */
            .plm-sb {
                position:fixed; top:0; left:0; bottom:0;
                width:var(--sw); background:var(--sb);
                border-right:1px solid var(--sbr);
                display:flex; flex-direction:column;
                z-index:1050; font-family:var(--sf);
                transition:width var(--se), transform var(--se);
                overflow:hidden;
            }
            .plm-sb::after {
                content:''; position:absolute; top:0; left:0; right:0; height:2px;
                background:linear-gradient(90deg,transparent,var(--sg) 40%,var(--sbl) 70%,transparent);
                pointer-events:none;
            }
            body.plm-collapsed .plm-sb { width:var(--swc); }
            @media(max-width:991px) {
                .plm-sb { transform:translateX(-100%); width:var(--sw) !important; box-shadow:8px 0 40px rgba(0,0,0,.6); }
                .plm-sb.mob-open { transform:translateX(0); }
            }

            /* Header */
            .plm-hdr {
                display:flex; align-items:center; gap:10px;
                padding:0 10px; height:60px; flex-shrink:0;
                border-bottom:1px solid var(--sbr); overflow:hidden;
            }
            .plm-logo {
                width:36px; height:36px; flex-shrink:0; border-radius:9px;
                background:linear-gradient(135deg,var(--sg),var(--sbl));
                display:flex; align-items:center; justify-content:center;
                box-shadow:0 0 16px rgba(63,185,80,.3); cursor:pointer;
            }
            .plm-logo i { color:#fff; font-size:16px; }
            .plm-logo img { width:20px; height:20px; object-fit:contain; filter:brightness(10); }

            .plm-brand { flex:1; overflow:hidden; min-width:0; }
            .plm-brand-n { display:block; font-size:13px; font-weight:600; color:var(--st); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
            .plm-brand-s { font-size:9px; color:var(--sm); font-family:var(--smo); letter-spacing:.6px; text-transform:uppercase; }

            body.plm-collapsed .plm-sb .plm-brand,
            body.plm-collapsed .plm-sb .plm-cbtn { display:none; }

            .plm-cbtn {
                width:28px; height:28px; flex-shrink:0; border-radius:7px;
                border:1px solid var(--sbr); background:var(--sb3); color:var(--sm);
                display:flex; align-items:center; justify-content:center;
                cursor:pointer; transition:all .2s;
            }
            .plm-cbtn:hover { background:var(--sb2); color:var(--st); }
            .plm-cbtn i { font-size:11px; }

            /* Expand button */
            .plm-expand-btn {
                display:none; width:100%; padding:10px 0;
                align-items:center; justify-content:center;
                cursor:pointer; border:none; background:transparent;
                color:var(--sm); border-bottom:1px solid var(--sbr);
                transition:background .2s, color .2s; flex-shrink:0;
            }
            .plm-expand-btn:hover { background:var(--sb2); color:var(--st); }
            .plm-expand-btn i { font-size:14px; }
            body.plm-collapsed .plm-sb .plm-expand-btn { display:flex; }

            /* Nav */
            .plm-nav { flex:1; overflow-y:auto; overflow-x:hidden; padding:8px; scrollbar-width:thin; scrollbar-color:var(--sb3) transparent; }
            .plm-nav::-webkit-scrollbar { width:3px; }
            .plm-nav::-webkit-scrollbar-thumb { background:var(--sb3); border-radius:3px; }

            /* Section label */
            .plm-lbl {
                padding:14px 8px 4px; font-size:9px; font-weight:600;
                font-family:var(--smo); letter-spacing:1.2px; text-transform:uppercase;
                color:var(--sm); white-space:nowrap; overflow:hidden;
                transition:opacity var(--se), height var(--se), padding var(--se);
            }
            body.plm-collapsed .plm-sb .plm-lbl { opacity:0; height:0; padding:0; pointer-events:none; }

            /* Nav item */
            .plm-ni {
                display:flex; align-items:center; gap:10px;
                padding:8px; border-radius:8px; cursor:pointer;
                color:var(--sm); position:relative;
                margin-bottom:1px; white-space:nowrap; user-select:none;
                border:1px solid transparent;
                transition:background .15s, color .15s, border-color .15s;
            }
            .plm-ni:hover { background:var(--sb2); color:var(--st); }
            .plm-ni--on {
                background:rgba(63,185,80,.1); color:var(--st) !important;
                border-color:rgba(63,185,80,.18);
            }
            .plm-ni--on::before {
                content:''; position:absolute; left:-1px; top:25%; bottom:25%;
                width:3px; background:linear-gradient(var(--sg),var(--sbl));
                border-radius:0 3px 3px 0;
            }
            body.plm-collapsed .plm-sb .plm-ni { justify-content:center; padding:9px 8px; }

            /* Icon wrap */
            .plm-iw {
                width:32px; height:32px; flex-shrink:0; border-radius:8px;
                background:var(--sb3); display:flex; align-items:center;
                justify-content:center; transition:background .2s, box-shadow .2s;
            }
            .plm-ni:hover .plm-iw, .plm-ni--on .plm-iw {
                background:linear-gradient(135deg,var(--sg),var(--sbl));
                box-shadow:0 2px 10px rgba(63,185,80,.28);
            }
            .plm-iw i { font-size:13px; color:var(--sm); transition:color .2s; }
            .plm-ni:hover .plm-iw i, .plm-ni--on .plm-iw i { color:#fff; }

            /* Label + chevron */
            .plm-nl { flex:1; font-size:13px; font-weight:500; overflow:hidden; text-overflow:ellipsis; }
            .plm-ch { font-size:10px; color:var(--sm); flex-shrink:0; transition:transform var(--se); }
            .plm-ch--o { transform:rotate(90deg); }
            body.plm-collapsed .plm-sb .plm-nl,
            body.plm-collapsed .plm-sb .plm-ch { display:none; }

            /* Tooltip when collapsed */
            body.plm-collapsed .plm-sb .plm-ni:hover::after {
                content:attr(data-tip);
                position:absolute; left:calc(100% + 10px); top:50%;
                transform:translateY(-50%);
                background:var(--sb3); color:var(--st); font-size:12px;
                padding:6px 10px; border-radius:7px; white-space:nowrap;
                border:1px solid var(--sbr); box-shadow:0 4px 20px rgba(0,0,0,.5);
                z-index:9999; pointer-events:none; font-family:var(--sf);
            }

            /* Sub group */
            .plm-sg { animation:sgIn .18s ease; overflow:hidden; }
            @keyframes sgIn { from{opacity:0;transform:translateY(-5px)} to{opacity:1;transform:translateY(0)} }
            body.plm-collapsed .plm-sb .plm-sg { display:none; }

            .plm-si {
                display:flex; align-items:center; gap:8px;
                padding:6px 10px 6px 50px; border-radius:7px; cursor:pointer;
                font-size:12.5px; color:var(--sm); margin-bottom:1px;
                transition:background .15s, color .15s; user-select:none; white-space:nowrap;
            }
            .plm-si:hover { background:var(--sb2); color:var(--st); }
            .plm-si--on { color:var(--sg) !important; background:rgba(63,185,80,.08); font-weight:500; }
            .plm-dot { width:4px; height:4px; border-radius:50%; background:var(--sm); flex-shrink:0; transition:background .15s; }
            .plm-si:hover .plm-dot, .plm-si--on .plm-dot { background:var(--sg); }

            /* Deep sub items (3rd level) */
            .plm-ssi {
                display:flex; align-items:center; gap:8px;
                padding:5px 10px 5px 66px; border-radius:7px; cursor:pointer;
                font-size:12px; color:var(--sm); margin-bottom:1px;
                transition:background .15s, color .15s; user-select:none; white-space:nowrap;
            }
            .plm-ssi:hover { background:var(--sb2); color:var(--st); }
            .plm-ssi--on { color:var(--sg) !important; background:rgba(63,185,80,.06); font-weight:500; }
            .plm-ssi-dot { width:3px; height:3px; border-radius:50%; background:var(--sm); flex-shrink:0; transition:background .15s; }
            .plm-ssi:hover .plm-ssi-dot, .plm-ssi--on .plm-ssi-dot { background:var(--sg); }

            /* ── FIX 2: Logout button ── */
            .plm-logout {
                display:flex; align-items:center; gap:8px;
                padding:9px 10px; margin:0 8px 15px; border-radius:8px;
                cursor:pointer; border:1px solid rgba(248,81,73,.18);
                background:rgba(248,81,73,.06); color:#f85149;
                font-size:12.5px; font-family:var(--sf); font-weight:500;
                transition:background .15s, border-color .15s, color .15s;
                flex-shrink:0; white-space:nowrap; overflow:hidden;
            }
            .plm-logout:hover {
                background:rgba(248,81,73,.14); border-color:rgba(248,81,73,.35);
                color:#ff6b64;
            }
            .plm-logout i { font-size:13px; flex-shrink:0; }
            .plm-logout-txt { overflow:hidden; text-overflow:ellipsis; }
            body.plm-collapsed .plm-sb .plm-logout { justify-content:center; padding:9px 8px; margin:0 6px 8px; }
            body.plm-collapsed .plm-sb .plm-logout-txt { display:none; }
            body.plm-collapsed .plm-sb .plm-logout:hover::after {
                content:'Log Out';
                position:absolute; left:calc(100% + 10px); top:50%;
                transform:translateY(-50%);
                background:var(--sb3); color:#f85149; font-size:12px;
                padding:6px 10px; border-radius:7px; white-space:nowrap;
                border:1px solid rgba(248,81,73,.2); box-shadow:0 4px 20px rgba(0,0,0,.5);
                z-index:9999; pointer-events:none;
            }
            body.plm-collapsed .plm-sb .plm-logout { position:relative; }

            /* Mobile hamburger */
            .plm-burger {
                display:none; position:fixed; top:14px; left:14px; z-index:1055;
                width:38px; height:38px; border-radius:8px;
                border:1px solid var(--sbr); background:var(--sb2); cursor:pointer;
                flex-direction:column; align-items:center; justify-content:center; gap:5px;
                box-shadow:0 4px 16px rgba(0,0,0,.4); transition:background .2s;
            }
            .plm-burger:hover { background:var(--sb3); }
            .plm-bar { width:17px; height:2px; background:var(--st); border-radius:2px; }
            @media(max-width:991px){ .plm-burger { display:flex; } }

            /* Divider */
            .plm-divider { height:1px; background:var(--sbr); margin:8px 4px; }
        `;
        document.head.appendChild(s);
    }

    _injectMobileBtn() {
        if (document.getElementById("plm-mobile-btn")) return;
        const btn = document.createElement("button");
        btn.id = "plm-mobile-btn";
        btn.className = "plm-burger";
        btn.innerHTML = `<span class="plm-bar"></span><span class="plm-bar"></span><span class="plm-bar"></span>`;
        btn.addEventListener("click", () => { this.state.mobileOpen = true; });
        document.body.appendChild(btn);
    }
}

registry.category("main_components").add("PlmSidebar", {
    Component: PlmSidebar,
    props: {},
});