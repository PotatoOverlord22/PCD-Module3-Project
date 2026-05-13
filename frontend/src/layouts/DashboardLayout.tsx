import {
    AppBar,
    Toolbar,
    Typography,
    Button,
    Tab,
    Tabs,
    Box,
    Container,
} from "@mui/material";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { clearToken, getRole } from "../api/client";

const TABS = [
    { label: "Anomalies", path: "/anomalies" },
    { label: "All Days", path: "/days" },
    { label: "Simulate", path: "/simulate" },
];

const ADMIN_TABS = [
    { label: "Evaluation", path: "/evaluation" },
    { label: "Audit Log", path: "/audit" },
];

export default function DashboardLayout() {
    const navigate = useNavigate();
    const location = useLocation();
    const role = getRole();

    const tabs = role === "admin" ? [...TABS, ...ADMIN_TABS] : TABS;

    const currentTab =
        tabs.find((t) => location.pathname.startsWith(t.path))?.path ?? "/anomalies";

    const handleLogout = () => {
        clearToken();
        navigate("/login");
    };

    return (
        <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        Caregiver Dashboard
                    </Typography>
                    <Typography variant="body2" sx={{ mr: 2 }}>
                        {role}
                    </Typography>
                    <Button
                        color="error"
                        variant="contained"
                        size="small"
                        onClick={handleLogout}
                    >
                        Logout
                    </Button>
                </Toolbar>
            </AppBar>

            <Container maxWidth="lg" sx={{ py: 3 }}>
                <Tabs
                    value={currentTab}
                    onChange={(_, path: string) => navigate(path)}
                    sx={{ mb: 3 }}
                >
                    {tabs.map((t) => (
                        <Tab key={t.path} label={t.label} value={t.path} />
                    ))}
                </Tabs>

                <Outlet />
            </Container>
        </Box>
    );
}
