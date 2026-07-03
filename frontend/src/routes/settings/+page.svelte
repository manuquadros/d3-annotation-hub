<script lang="ts">
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

<div class="settings-page">
    <h1>Settings</h1>

    <section class="card">
        <h2>Change Password</h2>
        <form onsubmit={handleChangePassword}>
            <div class="field">
                <label for="cp-current">Current password</label>
                <input
                    id="cp-current"
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
                    type="password"
                    bind:value={newPassword}
                    required
                    disabled={pending}
                    autocomplete="new-password"
                />
            </div>
            <div class="field">
                <label for="cp-confirm">Confirm new password</label>
                <input
                    id="cp-confirm"
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
    .settings-page {
        max-width: 480px;
        margin: 2rem auto;
        padding: 0 1rem;
    }

    h1 {
        font-size: 1.4rem;
        margin-bottom: 1.5rem;
    }

    .card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    h2 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 1.25rem;
    }

    .field {
        margin-bottom: 1.2rem;
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

    input[type="password"] {
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
        margin: 0 0 1rem;
    }

    .success {
        color: #166534;
        font-size: 0.875rem;
        margin: 0 0 1rem;
    }

    .actions {
        margin-top: 1.5rem;
    }
</style>
