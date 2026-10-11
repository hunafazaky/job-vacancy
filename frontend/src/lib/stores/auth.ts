import { writable } from 'svelte/store';
import { browser } from '$app/environment';

interface AuthState {
	accessToken: string | null;
	refreshToken: string | null;
}

function createAuthStore() {
	const initial: AuthState = browser
		? {
				accessToken: localStorage.getItem('access_token'),
				refreshToken: localStorage.getItem('refresh_token')
			}
		: { accessToken: null, refreshToken: null };

	const { subscribe, set } = writable<AuthState>(initial);

	return {
		subscribe,
		login(accessToken: string, refreshToken: string) {
			if (browser) {
				localStorage.setItem('access_token', accessToken);
				localStorage.setItem('refresh_token', refreshToken);
			}
			set({ accessToken, refreshToken });
		},
		logout() {
			if (browser) {
				localStorage.removeItem('access_token');
				localStorage.removeItem('refresh_token');
			}
			set({ accessToken: null, refreshToken: null });
		}
	};
}

export const auth = createAuthStore();
