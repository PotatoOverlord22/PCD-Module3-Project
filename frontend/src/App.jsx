import { useState, useEffect } from 'react';
import { login, api, apiPost, getToken, clearToken } from './api';
import './App.css';

function Login({ onLogin }) {
    const [username, setUsername] = useState('caregiver');
    const [password, setPassword] = useState('care123');
    const [error, setError] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        try {
            const data = await login(username, password);
            onLogin(data);
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={handleLogin}>
                <h2>🏠 Caregiver Dashboard</h2>
                <p className="subtitle">Explainable Activity Monitoring</p>
                <input type="text" value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" />
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" />
                <button type="submit">Login</button>
                {error && <p className="error">{error}</p>}
                <p className="hint">Users: caregiver/care123 or admin/admin123</p>
            </form>
        </div>
    );
}

function DayCard({ day, onClick }) {
    const hasAnomaly = Object.values(day.rooms).some(r => r.status === 'anomaly');
    return (
        <div className={`day-card ${hasAnomaly ? 'anomaly' : ''}`} onClick={() => onClick(day.date)}>
            <div className="day-date">{day.date} {hasAnomaly ? '⚠️' : '✅'}</div>
            <div className="room-badges">
                {Object.entries(day.rooms).map(([name, r]) => (
                    <span key={name} className={`badge ${r.status}`}>{name.toLowerCase()}</span>
                ))}
            </div>
        </div>
    );
}

function DayDetail({ date, onBack }) {
    const [data, setData] = useState(null);

    useEffect(() => {
        api(`/days/${date}`).then(setData);
    }, [date]);

    if (!data) return <p>Loading...</p>;

    return (
        <div className="detail-panel">
            <h3>📅 {data.date}</h3>
            {Object.entries(data.rooms).map(([room, info]) => (
                <div key={room} className="room-detail">
                    <h4>{room}: {info.status === 'anomaly' ? '⚠️ Anomaly' : '✅ Normal'} (score: {info.score})</h4>
                    {info.top_features && info.top_features.length > 0 && (
                        <div className="shap-bars">
                            {info.top_features.map((f, i) => (
                                <div key={i} className="feature-bar">
                                    <span className="bar-label">{f.time_slot}</span>
                                    <div className="bar" style={{ width: `${Math.min(Math.abs(f.shap_value) * 150, 200)}px` }} />
                                    <span className="bar-value">SHAP: {f.shap_value} | raw: {f.raw_value}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            ))}
            <button className="back-btn" onClick={onBack}>← Back</button>
        </div>
    );
}

function AnomaliesView() {
    const [anomalies, setAnomalies] = useState([]);
    const [selectedDate, setSelectedDate] = useState(null);

    useEffect(() => {
        api('/anomalies').then(setAnomalies);
    }, []);

    if (selectedDate) return <DayDetail date={selectedDate} onBack={() => setSelectedDate(null)} />;

    return (
        <>
            <div className="stats">
                <div className="stat-card"><div className="stat-value">{anomalies.length}</div><div className="stat-label">Anomalous Days</div></div>
                <div className="stat-card"><div className="stat-value">4</div><div className="stat-label">Rooms</div></div>
                <div className="stat-card"><div className="stat-value">128</div><div className="stat-label">Test Days</div></div>
            </div>
            <div className="day-list">
                {anomalies.map(d => <DayCard key={d.date} day={d} onClick={setSelectedDate} />)}
            </div>
        </>
    );
}

function AllDaysView() {
    const [days, setDays] = useState([]);
    const [selectedDate, setSelectedDate] = useState(null);

    useEffect(() => {
        api('/days').then(setDays);
    }, []);

    if (selectedDate) return <DayDetail date={selectedDate} onBack={() => setSelectedDate(null)} />;

    return (
        <div className="day-list">
            {days.map(d => <DayCard key={d.date} day={d} onClick={setSelectedDate} />)}
        </div>
    );
}

function EvaluationView() {
    const [data, setData] = useState(null);

    useEffect(() => {
        api('/anomalies/evaluation').then(setData);
    }, []);

    if (!data) return <p>Loading...</p>;

    return (
        <div className="detail-panel">
            <h3>Model Performance</h3>
            <table className="eval-table">
                <thead>
                    <tr><th>Room</th><th>Precision</th><th>Recall</th><th>F1-Score</th><th>TP</th><th>FP</th><th>FN</th></tr>
                </thead>
                <tbody>
                    {Object.entries(data).map(([room, m]) => (
                        <tr key={room}>
                            <td>{room}</td>
                            <td>{m.precision}</td>
                            <td>{m.recall}</td>
                            <td>{m.f1_score}</td>
                            <td>{m.true_positives}</td>
                            <td>{m.false_positives}</td>
                            <td>{m.false_negatives}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function SimulateView() {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [fileName, setFileName] = useState('');

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        setFileName(file.name);
        setLoading(true);

        const text = await file.text();
        const lines = text.trim().split('\n').filter(l => l.trim());
        const events = [];
        for (const line of lines) {
            const parts = line.split(',');
            if (parts.length >= 4) {
                events.push({ time: parts[1].trim(), sensor: parts[2].trim(), state: parts[3].trim() });
            } else if (parts.length === 3) {
                events.push({ time: parts[0].trim(), sensor: parts[1].trim(), state: parts[2].trim() });
            }
        }

        const date = lines[0]?.split(',')[0]?.trim() || '2024-01-01';
        const res = await apiPost('/predict', { date, events });
        setResult(res);
        setLoading(false);
    };

    return (
        <div className="detail-panel">
            <h3>🔬 Simulate New Day (File Upload)</h3>
            <p style={{ color: '#666', marginBottom: '1rem' }}>
                Upload a CSV file with raw sensor events. Format: <code>date,time,sensor,state</code> (like aruba.csv) or <code>time,sensor,state</code>
            </p>
            <input
                type="file"
                accept=".csv,.txt"
                onChange={handleFileUpload}
                style={{ marginBottom: '1rem' }}
            />
            {fileName && <p style={{ fontSize: '0.85rem', color: '#666' }}>File: {fileName}</p>}
            {loading && <p>Running model...</p>}

            {result && (
                <div style={{ marginTop: '1.5rem' }}>
                    <h4>Results for {result.date} ({result.total_events} events processed)</h4>
                    {Object.entries(result.rooms).map(([room, info]) => (
                        <div key={room} className="room-detail">
                            <h4>{room}: {info.status === 'anomaly' ? '⚠️ Anomaly' : '✅ Normal'} (score: {info.score})</h4>
                            {info.top_features && info.top_features.length > 0 && (
                                <div className="shap-bars">
                                    {info.top_features.map((f, i) => (
                                        <div key={i} className="feature-bar">
                                            <span className="bar-label">{f.time_slot}</span>
                                            <div className="bar" style={{ width: `${Math.min(Math.abs(f.shap_value) * 150, 200)}px` }} />
                                            <span className="bar-value">SHAP: {f.shap_value} | raw: {f.raw_value}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function AuditView() {
    const [entries, setEntries] = useState([]);

    useEffect(() => {
        api('/audit').then(setEntries);
    }, []);

    return (
        <table className="eval-table">
            <thead>
                <tr><th>Time</th><th>User</th><th>Action</th></tr>
            </thead>
            <tbody>
                {entries.slice(0, 50).map((e, i) => (
                    <tr key={i}>
                        <td>{e.timestamp?.slice(11, 19)}</td>
                        <td>{e.user}</td>
                        <td>{e.action || `${e.method} ${e.path}`}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

export default function App() {
    const [user, setUser] = useState(null);
    const [tab, setTab] = useState('anomalies');

    useEffect(() => {
        if (getToken()) setUser({ role: 'caregiver' });
    }, []);

    const handleLogin = (data) => setUser({ username: data.role, role: data.role });
    const handleLogout = () => { clearToken(); setUser(null); };

    if (!user) return <Login onLogin={handleLogin} />;

    return (
        <div className="app">
            <header className="header">
                <h1>🏠 Caregiver Dashboard</h1>
                <div className="user-info">
                    <span>{user.role}</span>
                    <button onClick={handleLogout} className="logout-btn">Logout</button>
                </div>
            </header>
            <div className="container">
                <nav className="tabs">
                    <button className={tab === 'anomalies' ? 'active' : ''} onClick={() => setTab('anomalies')}>Anomalies</button>
                    <button className={tab === 'all-days' ? 'active' : ''} onClick={() => setTab('all-days')}>All Days</button>
                    <button className={tab === 'simulate' ? 'active' : ''} onClick={() => setTab('simulate')}>Simulate</button>
                    <button className={tab === 'evaluation' ? 'active' : ''} onClick={() => setTab('evaluation')}>Evaluation</button>
                    {user.role === 'admin' && <button className={tab === 'audit' ? 'active' : ''} onClick={() => setTab('audit')}>Audit Log</button>}
                </nav>
                <main>
                    {tab === 'anomalies' && <AnomaliesView />}
                    {tab === 'all-days' && <AllDaysView />}
                    {tab === 'simulate' && <SimulateView />}
                    {tab === 'evaluation' && <EvaluationView />}
                    {tab === 'audit' && <AuditView />}
                </main>
            </div>
        </div>
    );
}
