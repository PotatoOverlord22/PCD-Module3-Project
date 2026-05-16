import { z } from "zod/v4";

export const FeatureSchema = z.object({
    time_slot: z.string(),
    shap_value: z.number(),
    raw_value: z.number(),
});

export type Feature = z.infer<typeof FeatureSchema>;

export const RoomInfoSchema = z.object({
    status: z.enum(["normal", "anomaly"]),
    score: z.number(),
    top_features: z.array(FeatureSchema).optional().default([]),
    explanation: z.string().nullable().optional().default(null),
});

export type RoomInfo = z.infer<typeof RoomInfoSchema>;

export const DaySummarySchema = z.object({
    date: z.string(),
    rooms: z.record(z.string(), RoomInfoSchema),
    // Names of rooms whose data was redacted server-side for the current role.
    // Caregivers see this populated (e.g. ["BATHROOM"]); the matching rooms
    // do NOT appear in `rooms`. Admins see this empty/undefined.
    redacted_rooms: z.array(z.string()).optional().default([]),
});

export type DaySummary = z.infer<typeof DaySummarySchema>;

export const DaySummaryListSchema = z.array(DaySummarySchema);
