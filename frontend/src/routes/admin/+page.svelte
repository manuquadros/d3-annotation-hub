<script lang="ts">
    import { untrack } from "svelte";
    import OntologyImportForm from "$lib/components/OntologyImportForm.svelte";
    import type { ImportedResult } from "$lib/components/OntologyImportForm.svelte";
    import CurieEditor from "$lib/components/CurieEditor.svelte";

    interface Ontology {
        ontology_id: number;
        name: string;
        prefix: string;
        uri: string;
        version: string | null;
    }

    interface Entity {
        entity_id: string;
        preferred_name: string;
        kind: string;
    }

    interface ProjectMember {
        user_id: string;
        email: string;
        roles: string[];
    }

    interface Project {
        project_id: number;
        name: string;
        description: string | null;
        required_annotators: number;
    }

    const PAGE_SIZE = 50;

    interface UserRecord {
        user_id: string;
        email: string;
        is_super_user: boolean;
        can_manage: boolean;
        disabled: boolean;
    }

    function userRoleLabel(u: UserRecord): string {
        if (u.is_super_user) return "Super user";
        if (u.can_manage) return "Project manager";
        return "User";
    }

    async function setCanManage(u: UserRecord, can_manage: boolean) {
        const res = await fetch(`/api/admin/users/${encodeURIComponent(u.email)}/permissions`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_super_user: u.is_super_user, can_manage }),
        });
        if (res.ok) {
            allUsers = allUsers.map((x) => (x.user_id === u.user_id ? { ...x, can_manage } : x));
        }
    }

    let confirmAction = $state<{ userId: string; kind: "remove-manager" | "remove-user" } | null>(null);

    async function fetchPassphrase(): Promise<string> {
        const res = await fetch("/api/admin/passphrase-suggestion");
        return res.ok ? res.json() : "";
    }

    let showAddUser = $state(false);
    let newUserEmail = $state("");
    let newUserPassphrase = $state("");
    let addUserPending = $state(false);
    let addUserError = $state<string | null>(null);
    let addUserCreated = $state<{ email: string; passphrase: string } | null>(null);
    let passphraseNoticeCopied = $state(false);

    function copyPassphrase(text: string) {
        navigator.clipboard.writeText(text).then(() => {
            passphraseNoticeCopied = true;
            setTimeout(() => { passphraseNoticeCopied = false; }, 2000);
        });
    }

    let removeUserPending = $state(false);

    async function handleRemoveUser(u: UserRecord) {
        removeUserPending = true;
        try {
            const res = await fetch(
                `/api/admin/users/${encodeURIComponent(u.email)}`,
                { method: "DELETE" },
            );
            if (res.ok) {
                const { action } = await res.json();
                if (action === "deleted") {
                    allUsers = allUsers.filter((x) => x.user_id !== u.user_id);
                } else {
                    allUsers = allUsers.map((x) =>
                        x.user_id === u.user_id ? { ...x, disabled: true } : x,
                    );
                }
            }
        } finally {
            removeUserPending = false;
            confirmAction = null;
        }
    }

    async function handleAddUser(e: SubmitEvent) {
        e.preventDefault();
        addUserPending = true;
        addUserError = null;
        addUserCreated = null;
        try {
            const res = await fetch("/api/admin/users", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: newUserEmail, password: newUserPassphrase }),
            });
            if (!res.ok) {
                const d = await res.json().catch(() => ({ detail: res.statusText }));
                addUserError = d.detail ?? res.statusText;
                return;
            }
            const created: UserRecord = await res.json();
            allUsers = [...allUsers, created];
            addUserCreated = { email: created.email, passphrase: newUserPassphrase };
            showAddUser = false;
        } finally {
            addUserPending = false;
        }
    }

    let { data } = $props();
    let ontologies = $state<Ontology[]>(untrack(() => data.ontologies));
    let allUsers = $state<UserRecord[]>(untrack(() => data.allUsers ?? []));

    let projects = $state<Project[]>(untrack(() => data.projects));

    // Per-project expanded panel
    let expandedProjectId = $state<number | null>(null);
    let projectMembers = $state<Record<number, ProjectMember[]>>({});
    let membersLoading = $state(false);

    async function toggleProject(projectId: number) {
        if (expandedProjectId === projectId) {
            expandedProjectId = null;
            return;
        }
        expandedProjectId = projectId;
        if (!projectMembers[projectId]) {
            membersLoading = true;
            try {
                const res = await fetch(`/api/projects/${projectId}/members`);
                if (res.ok) projectMembers[projectId] = await res.json();
            } finally {
                membersLoading = false;
            }
        }
    }

    let addMemberEmail = $state("");
    let addMemberRole = $state("annotator");
    let addMemberPending = $state(false);
    let addMemberError = $state<string | null>(null);
    let generatedPassword = $state<string | null>(null);

    async function handleAddMember(projectId: number) {
        addMemberPending = true;
        addMemberError = null;
        generatedPassword = null;
        try {
            const res = await fetch(`/api/projects/${projectId}/members`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: addMemberEmail, role: addMemberRole }),
            });
            if (!res.ok) {
                const d = await res.json().catch(() => ({ detail: res.statusText }));
                addMemberError = d.detail ?? res.statusText;
            } else {
                const member = await res.json();
                if (member.generated_password) generatedPassword = member.generated_password;
                const existing = projectMembers[projectId] ?? [];
                const idx = existing.findIndex((m) => m.user_id === member.user_id);
                if (idx >= 0) {
                    projectMembers[projectId] = existing.map((m, i) =>
                        i === idx ? { ...m, roles: member.roles } : m,
                    );
                } else {
                    projectMembers[projectId] = [
                        ...existing,
                        { user_id: member.user_id, email: member.email, roles: member.roles },
                    ];
                }
                addMemberEmail = "";
            }
        } finally {
            addMemberPending = false;
        }
    }

    async function handleRemoveMember(projectId: number, userId: string, role: string) {
        const res = await fetch(
            `/api/projects/${projectId}/members/${userId}/${role}`,
            { method: "DELETE" },
        );
        if (res.ok) {
            projectMembers[projectId] = (projectMembers[projectId] ?? [])
                .map((m) =>
                    m.user_id === userId
                        ? { ...m, roles: m.roles.filter((r) => r !== role) }
                        : m,
                )
                .filter((m) => m.roles.length > 0);
        }
    }

    let assignOntologyId = $state<Record<number, number | null>>({});
    let assignOntologyPending = $state<number | null>(null);

    async function handleAssignOntology(projectId: number) {
        const ontologyId = assignOntologyId[projectId];
        if (!ontologyId) return;
        assignOntologyPending = projectId;
        try {
            await fetch(`/api/projects/${projectId}/ontologies/${ontologyId}`, {
                method: "POST",
            });
        } finally {
            assignOntologyPending = null;
        }
    }


    async function handleImported(_result: ImportedResult) {
        const listRes = await fetch("/api/admin/ontology");
        if (listRes.ok) ontologies = await listRes.json();
    }

    let viewingId = $state<number | null>(null);
    let entities = $state<Entity[]>([]);
    let entityTotal = $state(0);
    let entityOffset = $state(0);
    let entityLoading = $state(false);

    async function loadEntities(ontologyId: number, offset: number) {
        entityLoading = true;
        try {
            const res = await fetch(
                `/api/admin/ontology/${ontologyId}?limit=${PAGE_SIZE}&offset=${offset}`,
            );
            if (!res.ok) return;
            const data = await res.json();
            entities = offset === 0 ? data.entities : [...entities, ...data.entities];
            entityTotal = data.total;
            entityOffset = offset + data.entities.length;
        } finally {
            entityLoading = false;
        }
    }

    function toggleView(ontologyId: number) {
        if (viewingId === ontologyId) {
            viewingId = null;
            entities = [];
            entityTotal = 0;
            entityOffset = 0;
        } else {
            viewingId = ontologyId;
            entities = [];
            entityOffset = 0;
            loadEntities(ontologyId, 0);
        }
    }

    interface ProposedEntity {
        entity_id: string;
        preferred_name: string;
        kind: string;
    }

    let proposedEntities = $state<ProposedEntity[]>(untrack(() => data.proposedEntities ?? []));
    let proposedTotal = $state<number>(untrack(() => data.proposedTotal ?? 0));
    let proposedOffset = $state(untrack(() => (data.proposedEntities ?? []).length));
    let proposedLoading = $state(false);

    async function loadMoreProposed() {
        proposedLoading = true;
        try {
            const res = await fetch(
                `/api/admin/proposed?limit=${PAGE_SIZE}&offset=${proposedOffset}`,
            );
            if (!res.ok) return;
            const d = await res.json();
            proposedEntities = [...proposedEntities, ...d.entities];
            proposedOffset += d.entities.length;
        } finally {
            proposedLoading = false;
        }
    }

    let confirmRejectId = $state<string | null>(null);
    let actionPending = $state<string | null>(null);

    async function handleAccept(curie: string) {
        actionPending = curie;
        try {
            const res = await fetch(
                `/api/admin/proposed/${encodeURIComponent(curie)}?action=confirm`,
                { method: "POST" },
            );
            if (res.ok) {
                proposedEntities = proposedEntities.filter((e) => e.entity_id !== curie);
                proposedTotal = Math.max(0, proposedTotal - 1);
                proposedOffset = Math.max(0, proposedOffset - 1);
            }
        } finally {
            actionPending = null;
        }
    }

    async function handleReject(curie: string) {
        actionPending = curie;
        try {
            const res = await fetch(`/api/admin/proposed/${encodeURIComponent(curie)}`, {
                method: "DELETE",
            });
            if (res.ok) {
                proposedEntities = proposedEntities.filter((e) => e.entity_id !== curie);
                proposedTotal = Math.max(0, proposedTotal - 1);
                proposedOffset = Math.max(0, proposedOffset - 1);
                confirmRejectId = null;
            }
        } finally {
            actionPending = null;
        }
    }

    async function renameProposedCurie(oldCurie: string, newCurie: string) {
        const res = await fetch(`/api/admin/proposed/${encodeURIComponent(oldCurie)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_curie: newCurie }),
        });
        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            throw new Error(body.detail ?? res.statusText);
        }
        proposedEntities = proposedEntities.map((e) =>
            e.entity_id === oldCurie ? { ...e, entity_id: newCurie } : e,
        );
    }

    let ftsRebuilding = $state(false);
    let ftsRebuildStatus = $state<'idle' | 'ok' | 'error'>('idle');

    async function handleRebuildFts() {
        ftsRebuilding = true;
        ftsRebuildStatus = 'idle';
        try {
            const res = await fetch('/api/admin/fts-rebuild', { method: 'POST' });
            ftsRebuildStatus = res.ok ? 'ok' : 'error';
        } catch {
            ftsRebuildStatus = 'error';
        } finally {
            ftsRebuilding = false;
        }
    }

    let confirmDeleteProjectId = $state<number | null>(null);
    let deletingProjectId = $state<number | null>(null);

    async function handleDeleteProject(projectId: number) {
        deletingProjectId = projectId;
        try {
            const res = await fetch(`/api/projects/${projectId}`, { method: "DELETE" });
            if (res.ok) {
                projects = projects.filter((p) => p.project_id !== projectId);
                if (expandedProjectId === projectId) expandedProjectId = null;
            }
        } finally {
            deletingProjectId = null;
            confirmDeleteProjectId = null;
        }
    }

    let confirmDeleteId = $state<number | null>(null);
    let deleting = $state(false);
    let deleteError = $state<string | null>(null);

    async function handleDelete(ontologyId: number) {
        deleting = true;
        deleteError = null;
        try {
            const res = await fetch(`/api/admin/ontology/${ontologyId}`, {
                method: "DELETE",
            });
            if (res.ok) {
                ontologies = ontologies.filter((o) => o.ontology_id !== ontologyId);
                if (viewingId === ontologyId) {
                    viewingId = null;
                    entities = [];
                }
                confirmDeleteId = null;
            } else {
                const body = await res.json().catch(() => ({ detail: res.statusText }));
                deleteError = body.detail ?? res.statusText;
            }
        } catch (err) {
            deleteError = String(err);
        } finally {
            deleting = false;
        }
    }
</script>

<div class="admin-page">
    <h1>Administration</h1>

    <section class="card">
        <div class="section-header">
            <h2>Projects</h2>
            <a href="/projects/new" class="btn small muted">+ New Project</a>
        </div>

        {#if projects.length === 0}
            <p class="empty">No projects yet.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Description</th>
                        <th>Annotators needed</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each projects as project (project.project_id)}
                        <tr class:expanded={expandedProjectId === project.project_id}>
                            <td><strong>{project.name}</strong></td>
                            <td class="muted">{project.description ?? "—"}</td>
                            <td>{project.required_annotators}</td>
                            <td class="actions-cell">
                                <button
                                    class="btn small muted"
                                    onclick={() => toggleProject(project.project_id)}
                                >
                                    {expandedProjectId === project.project_id ? "Hide" : "Manage"}
                                </button>
                                {#if confirmDeleteProjectId === project.project_id}
                                    <span class="confirm-prompt">Delete project?</span>
                                    <button
                                        class="btn small danger filled"
                                        disabled={deletingProjectId === project.project_id}
                                        onclick={() => handleDeleteProject(project.project_id)}
                                    >
                                        {deletingProjectId === project.project_id ? "…" : "Yes"}
                                    </button>
                                    <button
                                        class="btn small muted"
                                        onclick={() => (confirmDeleteProjectId = null)}
                                    >Cancel</button>
                                {:else}
                                    <button
                                        class="btn small danger"
                                        onclick={() => (confirmDeleteProjectId = project.project_id)}
                                    >Remove</button>
                                {/if}
                            </td>
                        </tr>

                        {#if expandedProjectId === project.project_id}
                            <tr class="project-panel-row">
                                <td colspan="4">
                                    <div class="project-panel">

                                        <div class="panel-section">
                                            <p class="panel-title">Members</p>
                                            {#if membersLoading}
                                                <p class="muted">Loading…</p>
                                            {:else if (projectMembers[project.project_id] ?? []).length === 0}
                                                <p class="empty">No members yet.</p>
                                            {:else}
                                                <table class="inner-table">
                                                    <thead>
                                                        <tr>
                                                            <th>Email</th>
                                                            <th>Roles</th>
                                                            <th></th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {#each projectMembers[project.project_id] as member (member.user_id)}
                                                            <tr>
                                                                <td>{member.email}</td>
                                                                <td>
                                                                    {#each member.roles as role (role)}
                                                                        <span class="role-badge">{role}</span>
                                                                    {/each}
                                                                </td>
                                                                <td class="actions-cell">
                                                                    {#each member.roles as role (role)}
                                                                        <button
                                                                            class="btn small danger"
                                                                            onclick={() =>
                                                                                handleRemoveMember(
                                                                                    project.project_id,
                                                                                    member.user_id,
                                                                                    role,
                                                                                )}
                                                                        >
                                                                            Remove {role}
                                                                        </button>
                                                                    {/each}
                                                                </td>
                                                            </tr>
                                                        {/each}
                                                    </tbody>
                                                </table>
                                            {/if}

                                            <form
                                                class="inline-form"
                                                onsubmit={(e) => {
                                                    e.preventDefault();
                                                    handleAddMember(project.project_id);
                                                }}
                                            >
                                                <input
                                                    type="email"
                                                    bind:value={addMemberEmail}
                                                    placeholder="user@example.com"
                                                    required
                                                />
                                                <select bind:value={addMemberRole}>
                                                    <option value="annotator">Annotator</option>
                                                    <option value="curator">Curator</option>
                                                    <option value="manager"
                                                        >Project manager</option
                                                    >
                                                </select>
                                                <button
                                                    type="submit"
                                                    class="btn small muted"
                                                    disabled={addMemberPending}
                                                >
                                                    {addMemberPending ? "…" : "Add"}
                                                </button>
                                            </form>
                                            {#if addMemberError}
                                                <p class="error">{addMemberError}</p>
                                            {/if}
                                            {#if generatedPassword}
                                                <div class="password-notice">
                                                    <strong>New user created.</strong> Share this
                                                    one-time password with them:
                                                    <code class="password">{generatedPassword}</code>
                                                </div>
                                            {/if}
                                        </div>

                                        {#if data.isSuperuser && ontologies.length > 0}
                                            <div class="panel-section">
                                                <p class="panel-title">Assign ontology</p>
                                                <div class="inline-form">
                                                    <select
                                                        bind:value={assignOntologyId[
                                                            project.project_id
                                                        ]}
                                                    >
                                                        <option value={null}>Select…</option>
                                                        {#each ontologies as onto (onto.ontology_id)}
                                                            <option value={onto.ontology_id}>
                                                                {onto.prefix} — {onto.name}
                                                            </option>
                                                        {/each}
                                                    </select>
                                                    <button
                                                        class="btn small muted"
                                                        disabled={!assignOntologyId[
                                                            project.project_id
                                                        ] ||
                                                            assignOntologyPending ===
                                                                project.project_id}
                                                        onclick={() =>
                                                            handleAssignOntology(project.project_id)}
                                                    >
                                                        {assignOntologyPending === project.project_id
                                                            ? "…"
                                                            : "Assign"}
                                                    </button>
                                                </div>
                                            </div>
                                        {/if}
                                    </div>
                                </td>
                            </tr>
                        {/if}
                    {/each}
                </tbody>
            </table>
        {/if}
    </section>

    {#if data.isSuperuser}
        <section class="card">
            <div class="section-header">
                <h2>User Management</h2>
                <button class="btn small muted" onclick={async () => {
                    showAddUser = !showAddUser;
                    addUserError = null;
                    addUserCreated = null;
                    if (showAddUser) {
                        newUserEmail = "";
                        newUserPassphrase = await fetchPassphrase();
                    }
                }}>
                    {showAddUser ? "Cancel" : "+ Add user"}
                </button>
            </div>

            {#if addUserCreated}
                <div class="password-notice">
                    <strong>User created.</strong> Share this passphrase with
                    <em>{addUserCreated.email}</em> — it will not be shown again:
                    <div class="passphrase-row">
                        <code class="password">{addUserCreated.passphrase}</code>
                        <button
                            type="button"
                            class="btn small muted"
                            title="Copy passphrase"
                            onclick={() => copyPassphrase(addUserCreated!.passphrase)}
                        >
                            {#if passphraseNoticeCopied}
                                <i class="ph ph-check"></i>
                            {:else}
                                <i class="ph ph-clipboard"></i>
                            {/if}
                        </button>
                    </div>
                </div>
            {/if}

            {#if showAddUser}
                <form onsubmit={handleAddUser} class="add-user-form">
                    <div class="field">
                        <label for="new-user-email">Email</label>
                        <input
                            id="new-user-email"
                            type="email"
                            bind:value={newUserEmail}
                            required
                            disabled={addUserPending}
                            placeholder="user@example.com"
                        />
                    </div>
                    <div class="field">
                        <label for="new-user-pass">Initial passphrase</label>
                        <div class="passphrase-row">
                            <input
                                id="new-user-pass"
                                type="text"
                                bind:value={newUserPassphrase}
                                required
                                disabled={addUserPending}
                            />
                            <button
                                type="button"
                                class="btn small muted"
                                title="Generate new passphrase"
                                disabled={addUserPending}
                                onclick={async () => (newUserPassphrase = await fetchPassphrase())}
                            >
                                <i class="ph ph-arrows-clockwise"></i>
                            </button>
                        </div>
                    </div>
                    {#if addUserError}
                        <p class="error">{addUserError}</p>
                    {/if}
                    <button type="submit" class="btn primary filled" disabled={addUserPending}>
                        {addUserPending ? "Creating…" : "Create user"}
                    </button>
                </form>
            {/if}

            {#if allUsers.length === 0}
                <p class="empty">No users found.</p>
            {:else}
                <table>
                    <thead>
                        <tr>
                            <th>Email</th>
                            <th>System role</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each allUsers as u (u.user_id)}
                            <tr class:disabled-row={u.disabled}>
                                <td>{u.email}</td>
                                <td>
                                    <span class="role-badge">{userRoleLabel(u)}</span>
                                    {#if u.disabled}
                                        <span class="role-badge disabled-badge">Disabled</span>
                                    {/if}
                                </td>
                                <td class="actions-cell">
                                    {#if !u.can_manage && !u.is_super_user && !u.disabled}
                                        <button
                                            class="btn small muted"
                                            onclick={() => setCanManage(u, true)}
                                        >
                                            Make project manager
                                        </button>
                                    {/if}
                                    {#if u.can_manage && !u.is_super_user && !u.disabled}
                                        {#if confirmAction?.userId === u.user_id && confirmAction.kind === "remove-manager"}
                                            <span class="confirm-prompt">Remove manager?</span>
                                            <button
                                                class="btn small danger filled"
                                                onclick={() => {
                                                    setCanManage(u, false);
                                                    confirmAction = null;
                                                }}
                                            >Yes</button>
                                            <button
                                                class="btn small muted"
                                                onclick={() => (confirmAction = null)}
                                            >Cancel</button>
                                        {:else}
                                            <button
                                                class="btn small danger"
                                                onclick={() => (confirmAction = { userId: u.user_id, kind: "remove-manager" })}
                                            >
                                                Remove project manager
                                            </button>
                                        {/if}
                                    {/if}
                                    {#if !u.disabled}
                                        <span style="margin-left: auto; display: flex; gap: 0.4rem; align-items: center;">
                                            {#if confirmAction?.userId === u.user_id && confirmAction.kind === "remove-user"}
                                                <span class="confirm-prompt">Remove?</span>
                                                <button
                                                    class="btn small danger filled"
                                                    disabled={removeUserPending}
                                                    onclick={() => handleRemoveUser(u)}
                                                >
                                                    {removeUserPending ? "…" : "Yes"}
                                                </button>
                                                <button
                                                    class="btn small muted"
                                                    onclick={() => (confirmAction = null)}
                                                >Cancel</button>
                                            {:else}
                                                <button
                                                    class="btn small danger"
                                                    onclick={() => (confirmAction = { userId: u.user_id, kind: "remove-user" })}
                                                >
                                                    Remove
                                                </button>
                                            {/if}
                                        </span>
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {/if}
        </section>

        <section class="card">
            <h2>Import OWL Ontology</h2>
            <OntologyImportForm onimported={handleImported} />
        </section>

        <section class="card">
            <h2>Loaded Ontologies</h2>
            {#if ontologies.length === 0}
                <p class="empty">No ontologies loaded yet.</p>
            {:else}
                <table>
                    <thead>
                        <tr>
                            <th>Prefix</th>
                            <th>Name</th>
                            <th>URI</th>
                            <th>Version</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each ontologies as onto (onto.ontology_id)}
                            <tr class:expanded={viewingId === onto.ontology_id}>
                                <td><code>{onto.prefix}</code></td>
                                <td>{onto.name}</td>
                                <td class="uri">{onto.uri}</td>
                                <td>{onto.version ?? "—"}</td>
                                <td class="actions-cell">
                                    {#if confirmDeleteId === onto.ontology_id}
                                        {#if deleteError}
                                            <span class="delete-error">{deleteError}</span>
                                            <button
                                                class="btn small muted"
                                                onclick={() => {
                                                    confirmDeleteId = null;
                                                    deleteError = null;
                                                }}
                                                >Dismiss</button
                                            >
                                        {:else}
                                            <span class="confirm-prompt">Remove?</span>
                                            <button
                                                class="btn small danger filled"
                                                disabled={deleting}
                                                onclick={() => handleDelete(onto.ontology_id)}
                                            >
                                                {deleting ? "…" : "Yes"}
                                            </button>
                                            <button
                                                class="btn small muted"
                                                onclick={() => (confirmDeleteId = null)}
                                                >Cancel</button
                                            >
                                        {/if}
                                    {:else}
                                        <button
                                            class="btn small muted"
                                            onclick={() => toggleView(onto.ontology_id)}
                                        >
                                            {viewingId === onto.ontology_id ? "Hide" : "View"}
                                        </button>
                                        <button
                                            class="btn small danger"
                                            onclick={() => (confirmDeleteId = onto.ontology_id)}
                                            >Remove</button
                                        >
                                    {/if}
                                </td>
                            </tr>

                            {#if viewingId === onto.ontology_id}
                                <tr class="entity-panel-row">
                                    <td colspan="5">
                                        <div class="entity-panel">
                                            <p class="entity-panel-header">
                                                {onto.name} —
                                                {entityLoading && entities.length === 0
                                                    ? "loading…"
                                                    : `${entityTotal.toLocaleString()} entities`}
                                            </p>
                                            {#if entities.length > 0}
                                                <table class="entity-table">
                                                    <thead>
                                                        <tr>
                                                            <th>CURIE</th>
                                                            <th>Name</th>
                                                            <th>Type</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {#each entities as e (e.entity_id)}
                                                            <tr>
                                                                <td><code>{e.entity_id}</code></td>
                                                                <td>{e.preferred_name}</td>
                                                                <td class="kind"
                                                                    >{e.kind || "—"}</td
                                                                >
                                                            </tr>
                                                        {/each}
                                                    </tbody>
                                                </table>
                                                {#if entityOffset < entityTotal}
                                                    <button
                                                        class="btn small muted load-more"
                                                        disabled={entityLoading}
                                                        onclick={() =>
                                                            loadEntities(
                                                                onto.ontology_id,
                                                                entityOffset,
                                                            )}
                                                    >
                                                        {entityLoading
                                                            ? "Loading…"
                                                            : `Load more (${entityTotal - entityOffset} remaining)`}
                                                    </button>
                                                {/if}
                                            {:else if !entityLoading}
                                                <p class="empty">No entities found.</p>
                                            {/if}
                                        </div>
                                    </td>
                                </tr>
                            {/if}
                        {/each}
                    </tbody>
                </table>
            {/if}
        </section>

        <section class="card">
            <h2>Proposed Entities <span class="proposed-count">({proposedTotal})</span></h2>
            {#if proposedEntities.length === 0}
                <p class="empty">No proposed entities.</p>
            {:else}
                <table class="entity-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Kind</th>
                            <th>CURIE</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each proposedEntities as e (e.entity_id)}
                            <tr>
                                <td>{e.preferred_name}</td>
                                <td class="kind">{e.kind || "—"}</td>
                                <td>
                                    <CurieEditor
                                        curie={e.entity_id}
                                        save={(newCurie) =>
                                            renameProposedCurie(
                                                e.entity_id,
                                                newCurie,
                                            )}
                                    />
                                </td>
                                <td class="actions-cell">
                                    {#if confirmRejectId === e.entity_id}
                                        <span class="confirm-prompt">Reject?</span>
                                        <button
                                            class="btn small danger filled"
                                            disabled={actionPending === e.entity_id}
                                            onclick={() => handleReject(e.entity_id)}
                                        >
                                            {actionPending === e.entity_id ? "…" : "Yes"}
                                        </button>
                                        <button
                                            class="btn small muted"
                                            onclick={() => (confirmRejectId = null)}
                                            >Cancel</button
                                        >
                                    {:else}
                                        <button
                                            class="btn small success"
                                            disabled={actionPending === e.entity_id}
                                            onclick={() => handleAccept(e.entity_id)}
                                            >Accept</button
                                        >
                                        <button
                                            class="btn small danger"
                                            onclick={() => (confirmRejectId = e.entity_id)}
                                            >Reject</button
                                        >
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
                {#if proposedOffset < proposedTotal}
                    <button
                        class="btn small muted load-more"
                        disabled={proposedLoading}
                        onclick={loadMoreProposed}
                    >
                        {proposedLoading
                            ? "Loading…"
                            : `Load more (${proposedTotal - proposedOffset} remaining)`}
                    </button>
                {/if}
            {/if}
        </section>

        <section class="card">
            <h2>Search Index</h2>
            <p class="hint">
                Rebuild the full-text search index if entities are missing from
                annotation search results.
            </p>
            <div class="fts-row">
                <button
                    class="btn secondary"
                    disabled={ftsRebuilding}
                    onclick={handleRebuildFts}
                >
                    {ftsRebuilding ? 'Rebuilding…' : 'Rebuild FTS index'}
                </button>
                {#if ftsRebuildStatus === 'ok'}
                    <span class="fts-ok">Index rebuilt successfully.</span>
                {:else if ftsRebuildStatus === 'error'}
                    <span class="fts-error">Rebuild failed.</span>
                {/if}
            </div>
        </section>
    {/if}
</div>

<style>
    .admin-page {
        max-width: 860px;
        margin: 2rem auto;
        padding: 0 1rem;
    }

    h1 {
        font-size: 1.4rem;
        margin-bottom: 1.5rem;
    }

    h2 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0;
    }

    .hint {
        font-size: 0.85rem;
        color: #666;
        margin: 0.4rem 0 0.8rem;
    }

    .fts-row {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .fts-ok {
        font-size: 0.85rem;
        color: #2a7a2a;
    }

    .fts-error {
        font-size: 0.85rem;
        color: #c00;
    }

    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.2rem;
    }

    .card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .add-user-form {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        border-top: 1px solid #eee;
        padding-top: 0.75rem;
        margin-bottom: 1.5rem;
    }

    .passphrase-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .passphrase-row input {
        flex: 1;
        min-width: 0;
        font-family: monospace;
    }

    .field {
        margin-bottom: 1rem;
    }

    label {
        display: block;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
        margin-bottom: 0.3rem;
    }

    input[type="text"],
    input[type="email"],
    select {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        box-sizing: border-box;
    }

    .error {
        color: #c00;
        font-size: 0.875rem;
        margin: 0.5rem 0 0;
    }

    .success {
        color: #080;
        font-size: 0.875rem;
        margin: 0.5rem 0 0;
    }

    .muted {
        color: #888;
        font-size: 0.875rem;
    }

    .empty {
        color: #888;
        font-size: 0.875rem;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }

    th {
        text-align: left;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #666;
        padding: 0.4rem 0.6rem;
        border-bottom: 2px solid #eee;
    }

    td {
        padding: 0.5rem 0.6rem;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: middle;
    }

    tr.expanded > td {
        border-bottom: none;
    }

    .uri {
        color: #555;
        font-size: 0.8rem;
        word-break: break-all;
    }

    .actions-cell {
        white-space: nowrap;
        display: flex;
        gap: 0.4rem;
        align-items: center;
    }

    .confirm-prompt {
        font-size: 0.8rem;
        color: #666;
        margin-right: 0.2rem;
    }

    .delete-error {
        font-size: 0.8rem;
        color: var(--color-error, #c00);
        margin-right: 0.4rem;
    }

    code {
        background: #f0f0f0;
        padding: 0.1em 0.3em;
        border-radius: 3px;
        font-size: 0.85em;
    }

    .project-panel-row > td {
        padding: 0;
        border-bottom: 2px solid #eee;
    }

    .project-panel {
        background: #fafafa;
        border-top: 1px solid #eee;
        padding: 1rem 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1.2rem;
    }

    .panel-section {
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
    }

    .panel-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #555;
        margin: 0;
    }

    .inline-form {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .inline-form input,
    .inline-form select {
        flex: 1;
        min-width: 0;
        padding: 0.25rem 0.5rem;
        font-size: 0.8rem;
    }

    .inner-table {
        font-size: 0.8rem;
    }

    .inner-table th {
        font-size: 0.7rem;
        padding: 0.3rem 0.5rem;
        border-bottom-width: 1px;
    }

    .inner-table td {
        padding: 0.3rem 0.5rem;
    }

    .role-badge {
        display: inline-block;
        padding: 0.1em 0.5em;
        background: #e8edf5;
        border-radius: 3px;
        font-size: 0.75rem;
        margin-right: 0.3rem;
        color: #334;
    }

    .disabled-badge {
        background: #f0e8e8;
        color: #833;
    }

    .disabled-row td {
        opacity: 0.55;
    }

    .password-notice {
        background: #fffbe6;
        border: 1px solid #f0d060;
        border-radius: 4px;
        padding: 0.6rem 0.8rem;
        font-size: 0.8rem;
    }

    .password {
        display: block;
        margin-top: 0.3rem;
        font-size: 1rem;
        letter-spacing: 0.05em;
        background: #fff;
        border: 1px solid #ddd;
        padding: 0.3em 0.6em;
        border-radius: 3px;
        user-select: all;
    }

    .entity-panel-row > td {
        padding: 0;
        border-bottom: 2px solid #eee;
    }

    .entity-panel {
        background: #fafafa;
        border-top: 1px solid #eee;
        padding: 1rem 1.5rem;
    }

    .entity-panel-header {
        font-size: 0.8rem;
        font-weight: 600;
        color: #555;
        margin: 0 0 0.8rem;
    }

    .entity-table {
        font-size: 0.8rem;
    }

    .entity-table th {
        font-size: 0.7rem;
        padding: 0.3rem 0.5rem;
    }

    .entity-table td {
        padding: 0.3rem 0.5rem;
    }

    .kind {
        color: #666;
        font-size: 0.75rem;
    }

    .load-more {
        margin-top: 0.8rem;
        width: 100%;
        text-align: center;
    }

    .proposed-count {
        font-weight: 400;
        color: #888;
        font-size: 0.9em;
    }

</style>
