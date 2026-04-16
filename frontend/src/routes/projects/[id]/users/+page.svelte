<script lang="ts">
    import { untrack } from "svelte";
    import "$lib/management.css";
    interface Member {
        user_id: string;
        email: string;
        roles: string[];
    }

    type LookupState =
        | { status: "idle" }
        | { status: "loading" }
        | { status: "found"; email: string }
        | { status: "not_found"; email: string }
        | { status: "error"; message: string };

    let { data } = $props();

    let members = $state<Member[]>(untrack(() => data.members));

    // Search form
    let searchEmail = $state("");
    let lookup = $state<LookupState>({ status: "idle" });

    // Add form (shown after lookup)
    let selectedRole = $state<"annotator" | "curator">("annotator");
    let newPassword = $state("");

    // Submission state
    let submitting = $state(false);
    let addError = $state<string | null>(null);
    let addedPassword = $state<string | null>(null); // generated password to show once

    async function handleSearch(e: SubmitEvent) {
        e.preventDefault();
        const email = searchEmail.trim();
        if (!email) return;

        lookup = { status: "loading" };
        addError = null;
        addedPassword = null;
        newPassword = "";
        selectedRole = "annotator";

        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/members/lookup?email=${encodeURIComponent(email)}`,
            );
            if (!res.ok) {
                lookup = { status: "error", message: res.statusText };
                return;
            }
            const body = await res.json();
            lookup = body.exists
                ? { status: "found", email: body.email }
                : { status: "not_found", email: email };
        } catch (err) {
            lookup = { status: "error", message: String(err) };
        }
    }

    async function handleAdd(e: SubmitEvent) {
        e.preventDefault();
        if (lookup.status !== "found" && lookup.status !== "not_found") return;

        submitting = true;
        addError = null;
        addedPassword = null;

        const payload: Record<string, string> = {
            email: lookup.email,
            role: selectedRole,
        };
        if (lookup.status === "not_found" && newPassword) {
            payload.password = newPassword;
        }

        try {
            const res = await fetch(`/api/projects/${data.projectId}/members`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                const d = await res.json().catch(() => ({ detail: res.statusText }));
                addError = d.detail ?? res.statusText;
                return;
            }
            const member: Member & { generated_password?: string } = await res.json();
            if (member.generated_password) {
                addedPassword = member.generated_password;
            }
            // Refresh member list
            const listRes = await fetch(`/api/projects/${data.projectId}/members`);
            if (listRes.ok) members = await listRes.json();
            // Reset form
            searchEmail = "";
            newPassword = "";
            lookup = { status: "idle" };
        } catch (err) {
            addError = String(err);
        } finally {
            submitting = false;
        }
    }

    async function handleRemoveRole(userId: string, role: string) {
        try {
            await fetch(`/api/projects/${data.projectId}/members/${userId}/${role}`, {
                method: "DELETE",
            });
            const listRes = await fetch(`/api/projects/${data.projectId}/members`);
            if (listRes.ok) members = await listRes.json();
        } catch {
            // ignore
        }
    }

    function roleLabel(role: string): string {
        return role === "manager"
            ? "Manager"
            : role.charAt(0).toUpperCase() + role.slice(1);
    }
</script>

<div class="page">
    <h1>Users</h1>

    <section class="card">
        <h2>Add user to project</h2>

        <form onsubmit={handleSearch} class="search-row">
            <input
                type="email"
                bind:value={searchEmail}
                placeholder="user@example.com"
                required
                disabled={submitting}
            />
            <button
                type="submit"
                class="btn-secondary"
                disabled={submitting || !searchEmail.trim()}
            >
                Search
            </button>
        </form>

        {#if lookup.status === "loading"}
            <p class="hint">Searching…</p>
        {:else if lookup.status === "error"}
            <p class="error">{lookup.message}</p>
        {:else if lookup.status === "found" || lookup.status === "not_found"}
            {#if lookup.status === "not_found"}
                <p class="warn">
                    No account found for <strong>{lookup.email}</strong>. A new
                    user will be created.
                </p>
            {:else}
                <p class="hint">
                    User <strong>{lookup.email}</strong> found.
                </p>
            {/if}

            <form onsubmit={handleAdd} class="add-form">
                <div class="field">
                    <label for="role">Role</label>
                    <select id="role" bind:value={selectedRole} disabled={submitting}>
                        <option value="annotator">Annotator</option>
                        <option value="curator">Curator</option>
                    </select>
                </div>

                {#if lookup.status === "not_found"}
                    <div class="field">
                        <label for="password">Initial password</label>
                        <input
                            id="password"
                            type="password"
                            bind:value={newPassword}
                            placeholder="Leave blank to generate one"
                            disabled={submitting}
                            autocomplete="new-password"
                        />
                    </div>
                {/if}

                {#if addError}
                    <p class="error">{addError}</p>
                {/if}

                <button type="submit" class="btn-primary" disabled={submitting}>
                    {submitting ? "Adding…" : lookup.status === "not_found" ? "Create & add" : "Add to project"}
                </button>
            </form>
        {/if}

        {#if addedPassword}
            <div class="generated-password">
                <p>
                    User created. Share this one-time password — it will not be
                    shown again:
                </p>
                <code>{addedPassword}</code>
            </div>
        {/if}
    </section>

    {#if members.length > 0}
        <section class="card">
            <h2>Project members ({members.length})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Roles</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each members as member (member.user_id)}
                        <tr>
                            <td class="email">{member.email}</td>
                            <td>
                                <div class="role-list">
                                    {#each member.roles as role}
                                        <span class="role-badge">{roleLabel(role)}</span>
                                    {/each}
                                </div>
                            </td>
                            <td class="actions">
                                {#each member.roles.filter((r) => r !== "manager") as role}
                                    <button
                                        class="btn-danger-sm"
                                        onclick={() => handleRemoveRole(member.user_id, role)}
                                        title="Remove {roleLabel(role)} role"
                                    >
                                        Remove {roleLabel(role)}
                                    </button>
                                {/each}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </section>
    {/if}
</div>

<style>
    .warn {
        font-size: 0.9rem;
        color: #7a5500;
        background: #fffbea;
        border: 1px solid #f5d67a;
        border-radius: 4px;
        padding: 0.5rem 0.75rem;
        margin: 0;
    }

    .search-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .search-row input {
        flex: 1;
        padding: 0.45rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.9rem;
    }

    .add-form {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        border-top: 1px solid #eee;
        padding-top: 0.75rem;
    }

    .field select,
    .field input {
        padding: 0.45rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.9rem;
        max-width: 320px;
    }

    .generated-password {
        background: #f0f7f0;
        border: 1px solid #c3dfc3;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        font-size: 0.9rem;
    }

    .generated-password p {
        margin: 0 0 0.4rem;
    }

    .generated-password code {
        font-family: monospace;
        font-size: 1rem;
        background: #e8f5e8;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
    }

    td.email {
        font-weight: 500;
    }

    td.actions {
        text-align: right;
        white-space: nowrap;
    }

    .role-list {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
    }

    .role-badge {
        background: #eef2ff;
        color: #3730a3;
        font-size: 0.8rem;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
    }
</style>
