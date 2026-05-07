<script lang="ts">
    import { untrack } from "svelte";
    import "$lib/styles/management.css";

    interface Member {
        user_id: string;
        email: string;
        roles: string[];
    }

    interface UserHit {
        user_id: string;
        email: string;
    }

    type LookupState =
        | { status: "idle" }
        | { status: "found"; email: string }
        | { status: "not_found"; email: string }
        | { status: "error"; message: string };

    const PROJECT_ROLES = ["annotator", "curator"] as const;
    type ProjectRole = (typeof PROJECT_ROLES)[number];
    const ROLE_ICONS: Record<ProjectRole, string> = {
        annotator: "ph-pencil-simple",
        curator: "ph-seal-check",
    };

    let { data } = $props();

    let members = $state<Member[]>(untrack(() => data.members));

    let searchEmail = $state("");
    let suggestions = $state<UserHit[]>([]);
    let showDropdown = $state(false);
    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    let lookup = $state<LookupState>({ status: "idle" });
    let selectedRole = $state<ProjectRole>("annotator");

    let newUserEmail = $state("");
    let newPassword = $state("");
    let passphraseCopied = $state(false);

    let submitting = $state(false);
    let addError = $state<string | null>(null);
    let addedPassword = $state<string | null>(null);
    let toggleError = $state<string | null>(null);

    let confirmRemoveUserId = $state<string | null>(null);

    function handleSearchInput() {
        const q = searchEmail.trim();
        if (lookup.status !== "idle") {
            lookup = { status: "idle" };
            suggestions = [];
            addError = null;
        }
        clearTimeout(debounceTimer ?? undefined);
        if (q.length < 2) {
            suggestions = [];
            showDropdown = false;
            return;
        }
        debounceTimer = setTimeout(async () => {
            try {
                const res = await fetch(
                    `/api/projects/${data.projectId}/users/search?q=${encodeURIComponent(q)}`,
                );
                if (res.ok) suggestions = await res.json();
            } catch {
                suggestions = [];
            }
            showDropdown = true;
        }, 300);
    }

    function selectExisting(hit: UserHit) {
        searchEmail = hit.email;
        lookup = { status: "found", email: hit.email };
        showDropdown = false;
        suggestions = [];
        addError = null;
        newPassword = "";
    }

    async function selectCreateNew() {
        const email = searchEmail.trim();
        lookup = { status: "not_found", email };
        newUserEmail = email;
        showDropdown = false;
        addError = null;
        newPassword = "";
        passphraseCopied = false;
        const res = await fetch(`/api/admin/passphrase-suggestion`);
        if (res.ok) newPassword = await res.json();
    }

    function resetSearch() {
        lookup = { status: "idle" };
        searchEmail = "";
        newUserEmail = "";
        suggestions = [];
        showDropdown = false;
        newPassword = "";
        selectedRole = "annotator";
        addError = null;
    }

    function handleInputBlur() {
        setTimeout(() => { showDropdown = false; }, 150);
    }

    async function copyPassphrase() {
        await navigator.clipboard.writeText(newPassword);
        passphraseCopied = true;
        setTimeout(() => { passphraseCopied = false; }, 2000);
    }

    async function handleAdd(e: SubmitEvent) {
        e.preventDefault();
        if (lookup.status !== "found" && lookup.status !== "not_found") return;

        submitting = true;
        addError = null;
        addedPassword = null;

        const email = lookup.status === "not_found" ? newUserEmail.trim() : lookup.email;
        const payload: Record<string, string> = { email, role: selectedRole };
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
            addedPassword = member.generated_password ?? (lookup.status === "not_found" ? newPassword : null);
            const listRes = await fetch(`/api/projects/${data.projectId}/members`);
            if (listRes.ok) members = await listRes.json();
            searchEmail = "";
            newPassword = "";
            lookup = { status: "idle" };
        } catch (err) {
            addError = String(err);
        } finally {
            submitting = false;
        }
    }

    async function handleToggleRole(member: Member, role: string) {
        toggleError = null;
        const hasRole = member.roles.includes(role);
        if (hasRole) {
            const res = await fetch(
                `/api/projects/${data.projectId}/members/${member.user_id}/${role}`,
                { method: "DELETE" },
            );
            if (!res.ok) {
                toggleError = "Failed to remove role.";
                return;
            }
            member.roles = member.roles.filter((r) => r !== role);
        } else {
            const res = await fetch(`/api/projects/${data.projectId}/members`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: member.email, role }),
            });
            if (!res.ok) {
                toggleError = "Failed to add role.";
                return;
            }
            const updated: Member = await res.json();
            member.roles = updated.roles;
        }
    }

    async function handleRemoveUser(userId: string) {
        const res = await fetch(`/api/projects/${data.projectId}/members/${userId}`, {
            method: "DELETE",
        });
        if (!res.ok) {
            toggleError = "Failed to remove user.";
            return;
        }
        members = members.filter((m) => m.user_id !== userId);
        confirmRemoveUserId = null;
    }

    function roleLabel(role: string): string {
        return role === "manager" ? "Manager" : role.charAt(0).toUpperCase() + role.slice(1);
    }
</script>

<div class="page">
    <h1>Users</h1>

    <section class="card">
        <h2>Add user to project</h2>

        <div class="combobox-wrap">
            <div class="combobox">
                <input
                    type="search"
                    bind:value={searchEmail}
                    oninput={handleSearchInput}
                    onblur={handleInputBlur}
                    onfocus={() => searchEmail.trim().length >= 2 && (showDropdown = true)}
                    placeholder="Search by email…"
                    disabled={submitting || lookup.status !== "idle"}
                    autocomplete="off"
                />
                {#if lookup.status !== "idle"}
                    <button
                        type="button"
                        class="clear-btn"
                        onclick={resetSearch}
                        title="Clear selection"
                        disabled={submitting}
                    >
                        <i class="ph ph-x"></i>
                    </button>
                {/if}
            </div>

            {#if showDropdown}
                <ul class="dropdown" role="listbox">
                    {#each suggestions as hit (hit.user_id)}
                        <li
                            role="option"
                            aria-selected="false"
                            onmousedown={() => selectExisting(hit)}
                        >
                            <i class="ph ph-user"></i>
                            {hit.email}
                        </li>
                    {/each}
                    <li
                        role="option"
                        aria-selected="false"
                        class="create-option"
                        onmousedown={selectCreateNew}
                    >
                        <i class="ph ph-user-plus"></i>
                        Create new account for <strong>{searchEmail.trim()}</strong>
                    </li>
                </ul>
            {/if}
        </div>

        {#if lookup.status === "found"}
            <p class="hint">User <strong>{lookup.email}</strong> found.</p>
        {:else if lookup.status === "not_found"}
            <p class="warn">No account found. Fill in the details below to create one.</p>
        {:else if lookup.status === "error"}
            <p class="error">{lookup.message}</p>
        {/if}

        {#if lookup.status === "found" || lookup.status === "not_found"}
            <form onsubmit={handleAdd} class="add-form">
                {#if lookup.status === "not_found"}
                    <div class="field">
                        <label for="new-email">Email</label>
                        <input
                            id="new-email"
                            type="email"
                            bind:value={newUserEmail}
                            required
                            disabled={submitting}
                            placeholder="user@example.com"
                        />
                    </div>
                {/if}

                <div class="field">
                    <label for="role">Role</label>
                    <select id="role" bind:value={selectedRole} disabled={submitting}>
                        <option value="annotator">Annotator</option>
                        <option value="curator">Curator</option>
                    </select>
                </div>

                {#if lookup.status === "not_found"}
                    <div class="field">
                        <label for="password">Initial passphrase</label>
                        <div class="passphrase-row">
                            <input
                                id="password"
                                type="text"
                                bind:value={newPassword}
                                placeholder="Loading suggestion…"
                                disabled={submitting}
                                autocomplete="new-password"
                            />
                            <button
                                type="button"
                                class="btn-ghost-sm"
                                title="Copy passphrase"
                                disabled={submitting || !newPassword}
                                onclick={copyPassphrase}
                            >
                                <i class="ph {passphraseCopied ? 'ph-check' : 'ph-clipboard'}"></i>
                            </button>
                            <button
                                type="button"
                                class="btn-ghost-sm"
                                title="Generate new passphrase"
                                disabled={submitting}
                                onclick={async () => {
                                    const res = await fetch(`/api/admin/passphrase-suggestion`);
                                    if (res.ok) newPassword = await res.json();
                                }}
                            >
                                <i class="ph ph-arrows-clockwise"></i>
                            </button>
                        </div>
                    </div>
                {/if}

                {#if addError}
                    <p class="error">{addError}</p>
                {/if}

                <button type="submit" class="btn-primary" disabled={submitting}>
                    {submitting
                        ? "Adding…"
                        : lookup.status === "not_found"
                          ? "Create & add"
                          : "Add to project"}
                </button>
            </form>
        {/if}

        {#if addedPassword}
            <div class="generated-password">
                <p>User added. Share this passphrase — it will not be shown again:</p>
                <code>{addedPassword}</code>
            </div>
        {/if}
    </section>

    {#if members.length > 0}
        <section class="card">
            <h2>Project members ({members.length})</h2>
            {#if toggleError}
                <p class="error">{toggleError}</p>
            {/if}
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
                                <div class="role-toggles">
                                    {#each PROJECT_ROLES as role (role)}
                                        {@const active = member.roles.includes(role)}
                                        <button
                                            class="btn small {active ? 'secondary filled' : 'muted'}"
                                            onclick={() => handleToggleRole(member, role)}
                                            title="{active ? 'Remove' : 'Add'} {roleLabel(role)} role"
                                        >
                                            <i class="ph {ROLE_ICONS[role]}"></i>
                                            {roleLabel(role)}
                                        </button>
                                    {/each}
                                    {#if member.roles.includes("manager")}
                                        <button class="btn small muted filled" disabled>
                                            <i class="ph ph-briefcase"></i>
                                            Manager
                                        </button>
                                    {/if}
                                </div>
                            </td>
                            <td class="actions">
                                {#if confirmRemoveUserId === member.user_id}
                                    <span class="confirm-text">Remove from project?</span>
                                    <button
                                        class="btn small danger filled"
                                        onclick={() => handleRemoveUser(member.user_id)}
                                    >Yes</button>
                                    <button
                                        class="btn small muted"
                                        onclick={() => (confirmRemoveUserId = null)}
                                    >Cancel</button>
                                {:else}
                                    <button
                                        class="btn small danger"
                                        onclick={() => (confirmRemoveUserId = member.user_id)}
                                    >Remove user</button>
                                {/if}
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

    .combobox-wrap {
        position: relative;
    }

    .combobox {
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    .combobox input {
        flex: 1;
        padding: 0.45rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.9rem;
    }

    .combobox input:disabled {
        background: #f5f5f5;
        color: #555;
    }

    .clear-btn {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.3rem;
        color: #888;
        font-size: 1rem;
        line-height: 1;
        border-radius: 4px;
    }

    .clear-btn:hover {
        color: #333;
        background: #f0f0f0;
    }

    .dropdown {
        position: absolute;
        top: calc(100% + 4px);
        left: 0;
        right: 0;
        background: #fff;
        border: 1px solid #ccc;
        border-radius: 6px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        list-style: none;
        margin: 0;
        padding: 0.25rem 0;
        z-index: 100;
        max-height: 240px;
        overflow-y: auto;
    }

    .dropdown li {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        cursor: pointer;
        font-size: 0.9rem;
        color: #333;
    }

    .dropdown li:hover {
        background: #f5f5f5;
    }

    .dropdown li i {
        font-size: 1rem;
        color: #666;
        flex-shrink: 0;
    }

    .create-option {
        border-top: 1px solid #eee;
        color: #1a6e2b !important;
    }

    .create-option i {
        color: #1a6e2b !important;
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

    .passphrase-row {
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }

    .passphrase-row input {
        flex: 1;
        max-width: none;
        font-family: monospace;
    }

    .generated-password {
        background: #f0f7f0;
        border: 1px solid #c3dfc3;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        font-size: 0.9rem;
        margin-top: 0.75rem;
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

    .confirm-text {
        font-size: 0.85rem;
        color: #555;
        margin-right: 0.4rem;
    }

    .role-toggles {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        align-items: center;
    }

</style>
