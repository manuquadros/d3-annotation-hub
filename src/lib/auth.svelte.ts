import { browser } from "$app/environment";
import { goto } from "$app/navigation";

const TOKEN_KEY = "auth_token";

interface Token {
    access_token: string;
    token_type: string;
}

class AuthState {
    token = $state<string | null>(null);

    constructor() {
        if (browser) {
            this.token = localStorage.getItem(TOKEN_KEY);
        }
    }

    get isAuthenticated(): boolean {
        return this.token !== null;
    }

    async login(username: string, password: string): Promise<boolean> {
        try {
            const formData = new FormData();
            formData.append("username", username);
            formData.append("password", password);

            const response = await fetch("http://localhost:8000/token", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                return false;
            }

            const data: Token = await response.json();
            this.token = data.access_token;

            if (browser) {
                localStorage.setItem(TOKEN_KEY, data.access_token);
            }

            return true;
        } catch (error) {
            console.error("Login error:", error);
            return false;
        }
    }

    logout(): void {
        this.token = null;
        if (browser) {
            localStorage.removeItem(TOKEN_KEY);
        }
        goto("/login");
    }

    getToken(): string | null {
        return this.token;
    }
}

export const auth = new AuthState();
