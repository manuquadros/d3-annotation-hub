<script lang="ts">
    import { goto } from "$app/navigation";
    import { auth } from "$lib/auth.svelte";
    import "../../styles.css";

    let username = $state("");
    let password = $state("");
    let error = $state("");
    let isLoading = $state(false);

    async function handleSubmit(event: Event) {
        event.preventDefault();
        error = "";
        isLoading = true;

        const success = await auth.login(username, password);

        if (success) {
            goto("/");
        } else {
            error = "Invalid username or password";
            isLoading = false;
        }
    }
</script>

<div class="login-container">
    <div class="login-card">
        <h1>Annotation Hub</h1>
        <h2>Sign In</h2>

        <form onsubmit={handleSubmit}>
            <div class="form-group">
                <label for="username">Username</label>
                <input
                    id="username"
                    type="text"
                    bind:value={username}
                    required
                    disabled={isLoading}
                    placeholder="Enter your username"
                />
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input
                    id="password"
                    type="password"
                    bind:value={password}
                    required
                    disabled={isLoading}
                    placeholder="Enter your password"
                />
            </div>

            {#if error}
                <div class="error-message">{error}</div>
            {/if}

            <button type="submit" disabled={isLoading}>
                {isLoading ? "Signing in..." : "Sign In"}
            </button>
        </form>
    </div>
</div>
