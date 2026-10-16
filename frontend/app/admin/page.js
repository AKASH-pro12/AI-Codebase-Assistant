"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "../components/AppShell";
import ConfirmModal from "../components/ConfirmModal";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  getAdminStats,
  getAdminUsers,
  updateUserStatus,
  updateUserRole,
  getAdminAuditLogs,
  getAdminCodebases,
  adminDeleteCodebase,
} from "../lib/api";

export default function AdminPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState("users"); // "users" | "codebases" | "audit"

  // Data states
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [codebases, setCodebases] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modals
  const [actionTarget, setActionTarget] = useState(null); // { type: 'status' | 'role' | 'delete_codebase', data: ... }
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/admin/login");
      return;
    }

    if (!authLoading && user && user.role !== "admin") {
      showToast("Access denied: Administrator privileges required.", "error");
      router.push("/dashboard");
      return;
    }

    if (user?.role === "admin") {
      loadAdminData();
    }
  }, [user, authLoading, router]);

  async function loadAdminData() {
    setLoading(true);
    try {
      const [statsRes, usersRes, codebasesRes, auditRes] = await Promise.all([
        getAdminStats().catch(() => null),
        getAdminUsers().catch(() => ({ users: [] })),
        getAdminCodebases().catch(() => ({ codebases: [] })),
        getAdminAuditLogs().catch(() => ({ audit_logs: [] })),
      ]);

      setStats(statsRes);
      setUsers(usersRes.users || []);
      setCodebases(codebasesRes.codebases || []);
      setAuditLogs(auditRes.audit_logs || []);
    } catch (err) {
      showToast("Failed to load admin data", "error");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmAction() {
    if (!actionTarget) return;
    setProcessing(true);

    try {
      if (actionTarget.type === "status") {
        const newStatus = !actionTarget.data.is_active;
        await updateUserStatus(actionTarget.data.id, newStatus);
        showToast(
          `User account ${newStatus ? "activated" : "deactivated"} successfully`,
          "success"
        );
      } else if (actionTarget.type === "role") {
        const newRole = actionTarget.data.role === "admin" ? "user" : "admin";
        await updateUserRole(actionTarget.data.id, newRole);
        showToast(`User role updated to ${newRole}`, "success");
      } else if (actionTarget.type === "delete_codebase") {
        const targetId = actionTarget.data.codebase_id || actionTarget.data._id || actionTarget.data.id;
        await adminDeleteCodebase(targetId);
        showToast(`Codebase "${actionTarget.data.codebase_name}" deleted by admin`, "success");
      }
      setActionTarget(null);
      await loadAdminData();
    } catch (err) {
      showToast(err.message || "Action failed", "error");
    } finally {
      setProcessing(false);
    }
  }

  return (
    <AppShell title="Admin Center">
      <div className="space-y-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-500 border border-amber-500/30">
              Admin Privilege Level
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            System Administration & Control Center
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage users, monitor cross-organization repositories, and audit security events.
          </p>
        </div>

        {/* System Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Registered Users
            </p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">
              {stats?.total_users ?? "—"}
            </p>
            <p className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-1">
              {stats?.active_users ?? 0} active accounts
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Deactivated Accounts
            </p>
            <p className="text-2xl font-bold text-rose-600 dark:text-rose-400">
              {stats?.deactivated_users ?? "—"}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Access restricted
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Total Repositories
            </p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">
              {stats?.total_codebases ?? "—"}
            </p>
            <p className="text-[11px] text-indigo-500 mt-1">
              {stats?.total_chunks ?? 0} chunks embedded
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Audit Events
            </p>
            <p className="text-2xl font-bold text-slate-900 dark:text-white">
              {stats?.total_audit_logs ?? "—"}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Immutable audit records
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
          <button
            onClick={() => setActiveTab("users")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "users"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            User Accounts ({users.length})
          </button>
          <button
            onClick={() => setActiveTab("codebases")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "codebases"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            All Codebases ({codebases.length})
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "audit"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            Security Audit Trail ({auditLogs.length})
          </button>
        </div>

        {/* Tab 1: User Management */}
        {activeTab === "users" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <tr>
                    <th className="py-3 px-4">User</th>
                    <th className="py-3 px-4">Email</th>
                    <th className="py-3 px-4">Role</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Codebases</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-500">
                        No registered users found.
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => {
                      const isSelf = u.id === user?.id;
                      return (
                        <tr key={u._id || u.id || u.email} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                          <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                            {u.name} {isSelf && <span className="text-[10px] text-indigo-500 font-bold">(You)</span>}
                          </td>
                          <td className="py-3.5 px-4 font-mono text-slate-600 dark:text-slate-400">
                            {u.email}
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                u.role === "admin"
                                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                                  : "bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                              }`}
                            >
                              {u.role}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                u.is_active
                                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                  : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
                              }`}
                            >
                              {u.is_active ? "Active" : "Deactivated"}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-slate-600 dark:text-slate-400">
                            {u.codebase_count} repos
                          </td>
                          <td className="py-3.5 px-4 text-right space-x-2">
                            {/* Role Toggle */}
                            <button
                              onClick={() =>
                                setActionTarget({
                                  type: "role",
                                  data: u,
                                  title: `Change role to ${u.role === "admin" ? "User" : "Admin"}?`,
                                  message: `Are you sure you want to change ${u.name}'s role?`,
                                })
                              }
                              className="px-2.5 py-1 rounded-lg border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-[11px] font-medium transition"
                            >
                              {u.role === "admin" ? "Demote" : "Make Admin"}
                            </button>

                            {/* Status Toggle */}
                            <button
                              disabled={isSelf && u.is_active}
                              onClick={() =>
                                setActionTarget({
                                  type: "status",
                                  data: u,
                                  title: u.is_active ? "Deactivate Account" : "Activate Account",
                                  message: u.is_active
                                    ? `Deactivate ${u.name}'s account? They will be immediately blocked from signing in or calling APIs.`
                                    : `Reactivate ${u.name}'s account so they can log in again?`,
                                  isDestructive: u.is_active,
                                })
                              }
                              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition disabled:opacity-40 disabled:cursor-not-allowed ${
                                u.is_active
                                  ? "text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 border border-rose-200 dark:border-rose-900"
                                  : "text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900"
                              }`}
                            >
                              {u.is_active ? "Deactivate" : "Activate"}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Global Codebases */}
        {activeTab === "codebases" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Codebase Name</th>
                    <th className="py-3 px-4">Owner</th>
                    <th className="py-3 px-4">Files</th>
                    <th className="py-3 px-4">Uploaded Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {codebases.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No codebases uploaded yet.
                      </td>
                    </tr>
                  ) : (
                    codebases.map((cb) => (
                      <tr
                        key={cb._id || cb.codebase_id || cb.id || `${cb.user_email || 'user'}-${cb.codebase_name}-${cb.created_at || ''}`}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition"
                      >
                        <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                          {cb.codebase_name}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-slate-600 dark:text-slate-400">
                          {cb.user_email || "Unknown"}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600 dark:text-slate-400">
                          {cb.total_files || 0}
                        </td>
                        <td className="py-3.5 px-4 text-slate-500">
                          {cb.created_at ? new Date(cb.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() =>
                              setActionTarget({
                                type: "delete_codebase",
                                data: cb,
                                title: "Delete Codebase (Admin)",
                                message: `As an administrator, permanently remove "${cb.codebase_name}" owned by ${cb.user_email}? This action is irreversibly audited.`,
                                isDestructive: true,
                              })
                            }
                            className="px-2.5 py-1 rounded-lg text-[11px] font-medium text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 border border-rose-200 dark:border-rose-900 transition"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Security Audit Trail */}
        {activeTab === "audit" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  <tr>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Resource</th>
                    <th className="py-3 px-4">Details</th>
                    <th className="py-3 px-4">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-500">
                        No security audit events recorded yet.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log, idx) => (
                      <tr
                        key={log._id || log.id || `${log.timestamp}-${log.action}-${log.email}-${log.resource_id || idx}`}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition"
                      >
                      <td className="py-3 px-4 font-mono font-bold">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] ${
                            log.action.includes("DELETE")
                              ? "bg-rose-500/10 text-rose-500"
                              : log.action.includes("DEACTIVATE")
                              ? "bg-amber-500/10 text-amber-500"
                              : log.action.includes("LOGIN")
                              ? "bg-indigo-500/10 text-indigo-500"
                              : "bg-emerald-500/10 text-emerald-500"
                          }`}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-700 dark:text-slate-300">
                        {log.email}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-500">
                        {log.resource_type}: {log.resource_id ? log.resource_id.slice(0, 10) + "..." : "—"}
                      </td>
                      <td className="py-3 px-4 text-slate-500 truncate max-w-xs font-mono text-[11px]">
                        {JSON.stringify(log.details || {})}
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : "—"}
                      </td>
                    </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={!!actionTarget}
        title={actionTarget?.title || "Confirm Action"}
        message={actionTarget?.message || "Are you sure you want to proceed?"}
        confirmText="Confirm"
        cancelText="Cancel"
        isDestructive={actionTarget?.isDestructive}
        loading={processing}
        onConfirm={handleConfirmAction}
        onCancel={() => setActionTarget(null)}
      />
    </AppShell>
  );
}
