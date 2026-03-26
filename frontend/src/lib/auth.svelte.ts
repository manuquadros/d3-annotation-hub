import { goto } from "$app/navigation";

/** @internal */
class AuthState {
    isAuthenticated = $state(false);

    async login(username: string, password: string): Promise<boolean> {
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);

        const response = await fetch("/api/login", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) return false;

        this.isAuthenticated = true;
        return true;
    }

    logout(): void {
        this.isAuthenticated = false;
        fetch("/api/logout", { method: "POST" });
        goto("/login");
    }
}

export const auth = new AuthState();
