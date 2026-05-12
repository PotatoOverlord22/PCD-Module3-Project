const API = 'http://localhost:8000';

let token = localStorage.getItem('token') || '';

export function setToken(t) {
    token = t;
    localStorage.setItem('token', t);
}

export function getToken() {
    return token;
}

export function clearToken() {
    token = '';
    localStorage.removeItem('token');
}

export async function login(username, password) {
    const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `username=${username}&password=${password}`,
    });
    if (!res.ok) throw new Error('Invalid credentials');
    const data = await res.json();
    setToken(data.access_token);
    return data;
}

export async function api(path) {
    const res = await fetch(`${API}${path}`, {
        headers: { 'Authorization': `Bearer ${token}` },
    });
    if (res.status === 401) {
        clearToken();
        window.location.reload();
    }
    return res.json();
}

export async function apiPost(path, body) {
    const res = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
    });
    return res.json();
}
