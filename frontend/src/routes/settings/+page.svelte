<script lang="ts">
    import "$lib/styles/management.css";
    import { errorDetail } from "$lib/utils/http";

    let currentPassword = $state("");
    let newPassword = $state("");
    let confirmPassword = $state("");
    let pending = $state(false);
    let error = $state<string | null>(null);
    let success = $state(false);

    async function handleChangePassword(e: SubmitEvent) {
        e.preventDefault();
        if (newPassword !== confirmPassword) {
            error = "New passwords do not match";
            return;
        }
        pending = true;
        error = null;
        success = false;
        try {
            const res = await fetch("/api/me/change-password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            });
            if (!res.ok) {
                error = await errorDetail(res);
            } else {
                success = true;
                currentPassword = "";
                newPassword = "";
                confirmPassword = "";
            }
        } finally {
            pending = false;
        }
    }
</script>

<div class="page">
    <h1>Settings</h1>

    <section class="card">
        <h2>Change Password</h2>
        <form onsubmit={handleChangePassword}>
            <div class="field">
                <label for="cp-current">Current password</label>
                <input
                    id="cp-current"
                    class="form-control small"
                    type="password"
                    bind:value={currentPassword}
                    required
                    disabled={pending}
                    autocomplete="current-password"
                />
            </div>
            <div class="field">
                <label for="cp-new">New password</label>
                <input
                    id="cp-new"
                    class="form-control small"
                    type="password"
                    bind:value={newPassword}
                    required
                    minlength={8}
                    disabled={pending}
                    autocomplete="new-password"
                />
            </div>
            <div class="field">
                <label for="cp-confirm">Confirm new password</label>
                <input
                    id="cp-confirm"
                    class="form-control small"
                    type="password"
                    bind:value={confirmPassword}
                    required
                    disabled={pending}
                    autocomplete="new-password"
                />
            </div>

            {#if error}
                <p class="error">{error}</p>
            {/if}
            {#if success}
                <p class="success">Password changed successfully.</p>
            {/if}

            <div class="actions">
                <button
                    type="submit"
                    class="btn primary filled"
                    disabled={pending}
                >
                    {pending ? "Saving…" : "Change Password"}
                </button>
            </div>
        </form>
    </section>
</div>

<style>
    /* Shared `.page` is 900px, which strands this short single-column form.
       The narrow measure is a deliberate page-specific override, not a
       leftover private copy of the design system. */
    .page {
        max-width: 480px;
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .actions {
        margin-top: 0.75rem;
    }
</style>
