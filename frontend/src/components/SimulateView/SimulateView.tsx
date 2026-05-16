import { useState } from "react";
import {
    Paper,
    Typography,
    Box,
    CircularProgress,
    Alert,
} from "@mui/material";
import LockIcon from "@mui/icons-material/Lock";
import { FileDropzone, FileDropzoneBody } from "mui-file-upload";
import { postPredict } from "../../api/requests";
import { parseSensorCsv } from "../../utils/csv";
import type { PredictResponse } from "../../model/predict";
import "./SimulateView.scss";

export default function SimulateView() {
    const [result, setResult] = useState<PredictResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [fileName, setFileName] = useState("");
    const [errors, setErrors] = useState<string[]>([]);

    const handleFilesAccepted = async (files: File[]) => {
        const file = files[0];
        if (!file) return;

        setFileName(file.name);
        setLoading(true);
        setResult(null);
        setErrors([]);

        try {
            const text = await file.text();
            const parsed = parseSensorCsv(text);

            if (parsed.events.length === 0) {
                setErrors(parsed.errors);
                setLoading(false);
                return;
            }

            if (parsed.errors.length > 0) {
                setErrors(parsed.errors);
            }

            const res = await postPredict(parsed.date, parsed.events);
            setResult(res);
        } catch {
            setErrors(["Failed to run prediction. Please check the file and try again."]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
                Simulate New Day (File Upload)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Upload a CSV file with raw sensor events. Format:{" "}
                <code>date,time,sensor,state</code> or <code>time,sensor,state</code>
            </Typography>

            <FileDropzone
                acceptsOnly=".csv,.txt"
                onFilesAccepted={handleFilesAccepted}
                onFilesRejected={() => {}}
                dragZoneSx={(state) => ({
                    minHeight: 200,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "2px dashed",
                    borderColor: state.dragActive ? "primary.main" : "divider",
                    borderRadius: 2,
                    bgcolor: state.dragActive ? "action.hover" : "transparent",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    py: 4,
                    px: 2,
                })}
            >
                <FileDropzoneBody
                    title="Drag & drop a CSV file here, or click to browse"
                    dropTitle="Drop it here"
                />
            </FileDropzone>

            {fileName && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    File: {fileName}
                </Typography>
            )}

            {errors.map((err, i) => (
                <Alert key={i} severity={result ? "warning" : "error"} sx={{ mt: 1 }}>
                    {err}
                </Alert>
            ))}

            {loading && <CircularProgress sx={{ mt: 2, display: "block" }} />}

            {result && (
                <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                        Results for {result.date} ({result.total_events} events processed)
                    </Typography>

                    {result.redacted_rooms && result.redacted_rooms.length > 0 && (
                        <Alert severity="info" icon={<LockIcon />} sx={{ mb: 2 }}>
                            Results for {result.redacted_rooms.map((r) => r.toLowerCase()).join(", ")} are hidden for privacy.
                            Administrators with explicit authorization can view the full data.
                        </Alert>
                    )}

                    {Object.entries(result.rooms).map(([room, info]) => (
                        <Box key={room} sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
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
                                <Box sx={{ ml: 2, mt: 1 }}>
                                    {info.top_features.map((f, i) => (
                                        <Box key={i} className="simulate-view__feature-row">
                                            <Typography variant="body2" className="simulate-view__slot">
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
                </Box>
            )}
        </Paper>
    );
}
