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
});

export type DaySummary = z.infer<typeof DaySummarySchema>;

export const DaySummaryListSchema = z.array(DaySummarySchema);
