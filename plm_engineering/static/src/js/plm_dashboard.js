/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PlmDashboard extends Component {
    static template = "plm_engineering.PlmDashboard";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        updateActionState: { type: Function, optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true }, 

    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            error: false,
            data: null,
            lastRefresh: null,
            refreshing: false,
        });
        this.openEcoList = this.openEcoList.bind(this);
        this.openPendingApprovals = this.openPendingApprovals.bind(this);
        this.openProducts = this.openProducts.bind(this);
        this.openBoms = this.openBoms.bind(this);
        this.openEcoById = this.openEcoById.bind(this);
        this.openDoneEcos = this.openDoneEcos.bind(this);
        this.createNewEco = this.createNewEco.bind(this);
        this.openStageEcos = this.openStageEcos.bind(this);

        this._pollInterval = null;
        this._POLL_MS = 30000; // 30 seconds

        onMounted(async () => {
            await this._loadData();
            this._startPolling();
        });

        onWillUnmount(() => {
            this._stopPolling();
        });
    }


    async _loadData() {
        try {
            this.state.refreshing = true;
            const data = await this.orm.call("plm.dashboard", "get_dashboard_data", []);
            this.state.data = data;
            this.state.lastRefresh = new Date();
            this.state.error = false;
            this.state.loading = false;
        } catch (e) {
            this.state.error = true;
            this.state.loading = false;
            console.error("PLM Dashboard error:", e);
        } finally {
            this.state.refreshing = false;
        }
    }

    _startPolling() {
        this._pollInterval = setInterval(() => this._loadData(), this._POLL_MS);
    }

    _stopPolling() {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = null;
        }
    }

    async onRefresh() {
        await this._loadData();
        this.notification.add("Dashboard refreshed", {
            type: "success",
            sticky: false,
        });
    }

    get lastRefreshLabel() {
        if (!this.state.lastRefresh) return "";
        return this.state.lastRefresh.toLocaleTimeString();
    }

    get weeklyMax() {
        const trend = this.state.data?.weekly_trend || [];
        return Math.max(...trend.map((d) => d.count), 1);
    }

    get stageMax() {
        const pipeline = this.state.data?.stage_pipeline || [];
        return Math.max(...pipeline.map((s) => s.count), 1);
    }

    getPriorityLabel(key) {
        return { "0": "Normal", "1": "Important", "2": "Very Urgent", "3": "Critical" }[key] || key;
    }

    getPriorityColor(key) {
        return { "0": "#6c757d", "1": "#0d6efd", "2": "#fd7e14", "3": "#dc3545" }[key] || "#6c757d";
    }

    getStateColor(state) {
        return {
            draft: "#6c757d",
            in_review: "#ffc107",
            approved: "#0dcaf0",
            done: "#198754",
            cancelled: "#dc3545",
        }[state] || "#6c757d";
    }

    getStateLabel(state) {
        return {
            draft: "Draft",
            in_review: "In Review",
            approved: "Approved",
            done: "Done",
            cancelled: "Cancelled",
        }[state] || state;
    }

    getEcoTypeLabel(type) {
        return type === "product" ? "Product" : type === "bom" ? "BoM" : type;
    }

    getStageColor(stage) {
        if (stage.is_final) return "#198754";
        if (stage.is_approval) return "#ffc107";
        if (stage.is_start) return "#6c757d";
        return "#0d6efd";
    }

    formatDate(dateStr) {
        if (!dateStr) return "—";
        try {
            return new Date(dateStr).toLocaleDateString();
        } catch {
            return dateStr;
        }
    }

    formatDatetime(dateStr) {
        if (!dateStr) return "—";
        try {
            return new Date(dateStr).toLocaleString();
        } catch {
            return dateStr;
        }
    }

    barWidth(value, max) {
        return `${Math.round((value / max) * 100)}%`;
    }


    openEcoList = async () => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "All ECOs",
            res_model: "plm.eco",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            target: "current",
        });
    };

    openPendingApprovals = async () => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Approval",
            res_model: "plm.eco",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "in_review"]],
            target: "current",
        });
    };

    openProducts = async () => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active Products",
            res_model: "plm.product",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "active"]],
            target: "current",
        });
    };

    openBoms = async () => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active BoMs",
            res_model: "plm.bom",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "active"]],
            target: "current",
        });
    };

    openEcoById = async (ecoId) => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "plm.eco",
            res_id: ecoId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    };

    openDoneEcos = async () => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Applied ECOs",
            res_model: "plm.eco",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "done"]],
            target: "current",
        });
    };

    createNewEco = async () => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "New ECO",
            res_model: "plm.eco",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    };

    openStageEcos = async (stageId, stageName) => {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: `ECOs — ${stageName}`,
            res_model: "plm.eco",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [["stage_id", "=", stageId]],
            target: "current",
        });
    };
}
registry.category("actions").add("plm_engineering.plm_dashboard_action", PlmDashboard);
