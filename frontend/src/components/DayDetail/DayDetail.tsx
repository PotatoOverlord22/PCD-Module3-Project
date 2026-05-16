import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    Paper,
    Typography,
    Button,
    Box,
    LinearProgress,
    Alert,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import LockIcon from "@mui/icons-material/Lock";
import { getDayDetail } from "../../api/requests";
import type { DaySummary } from "../../model/day";
import "./DayDetail.scss";

export default function DayDetail() {
    const { date } = useParams<{ date: string }>();
    const navigate = useNavigate();
    const [data, setData] = useState<DaySummary | null>(null);

    useEffect(() => {
        if (date) {
            getDayDetail(date).then(setData);
        }
    }, [date]);

    if (!data) return <LinearProgress />;

    const redacted = data.redacted_rooms ?? [];

    return (
        <Paper className="day-detail" sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
                {data.date}
            </Typography>

            {redacted.length > 0 && (
                <Alert
                    severity="info"
                    icon={<LockIcon />}
                    sx={{ mb: 2 }}
                >
                    Activity in {redacted.map((r) => r.toLowerCase()).join(", ")} is hidden for privacy.
                    Administrators with explicit clinical authorization can view the full data.
                </Alert>
            )}

            {Object.entries(data.rooms).map(([room, info]) => (
                <Box key={room} className="day-detail__room" sx={{ mb: 2 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {room}: {info.status === "anomaly" ? "Anomaly" : "Normal"} (score:{" "}
                        {info.score})
                    </Typography>

                    {info.explanation && (
                        <Typography
                            variant="body2"
                            sx={{
                                ml: 2,
                                mt: 1,
                                p: 1.5,
                                bgcolor: "action.hover",
                                borderRadius: 1,
                                whiteSpace: "pre-line",
                                fontStyle: "italic",
                            }}
                        >
                            {info.explanation}
                        </Typography>
                    )}

                    {info.top_features && info.top_features.length > 0 && (
                        <Box className="day-detail__features" sx={{ ml: 2, mt: 1 }}>
                            {info.top_features.map((f, i) => (
                                <Box key={i} className="day-detail__feature-row">
                                    <Typography variant="body2" className="day-detail__slot">
                                        {f.time_slot}
                                    </Typography>
                                    <Box
                                        sx={{
                                            height: 18,
                                            bgcolor: "error.main",
                                            borderRadius: 1,
                                            minWidth: 5,
                                            mr: 1,
                                            width: `${Math.min(Math.abs(f.shap_value) * 150, 200)}px`,
                                        }}
                                    />
                                    <Typography variant="caption" color="text.secondary">
                                        SHAP: {f.shap_value} | raw: {f.raw_value}
                                    </Typography>
                                </Box>
                            ))}
                        </Box>
                    )}
                </Box>
            ))}

            <Button
                variant="contained"
                startIcon={<ArrowBackIcon />}
                onClick={() => navigate(-1)}
                sx={{ mt: 1 }}
            >
                Back
            </Button>
        </Paper>
    );
}
