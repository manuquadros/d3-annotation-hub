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

    async logout(): Promise<void> {
        this.isAuthenticated = false;
        await fetch("/api/logout", { method: "POST" });
        window.location.replace("/login");
    }
}

export const auth = new AuthState();
