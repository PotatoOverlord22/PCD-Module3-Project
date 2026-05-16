import { z } from "zod/v4";
import { RoomInfoSchema } from "./day";

export const SensorEventSchema = z.object({
    time: z.string(),
    sensor: z.string(),
    state: z.string(),
});

export type SensorEvent = z.infer<typeof SensorEventSchema>;

export const PredictRequestSchema = z.object({
    date: z.string(),
    events: z.array(SensorEventSchema),
});

export type PredictRequest = z.infer<typeof PredictRequestSchema>;

export const PredictResponseSchema = z.object({
    date: z.string(),
    rooms: z.record(z.string(), RoomInfoSchema),
    total_events: z.number(),
    redacted_rooms: z.array(z.string()).optional().default([]),
});

export type PredictResponse = z.infer<typeof PredictResponseSchema>;
