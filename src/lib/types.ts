import { z } from "zod";

export const Pointer = z.object({
    pointer_id: z.int(),
    user_id: z.uuid(),
    entity_id: z.string(),
    reference_id: z.int(),
    offset: z.int(),
    length: z.int(),
});
export type Pointer = z.infer<typeof Pointer>;

export type Entity = {
    entity_id: string;
    kind: string;
    designations: Set<string>;
};
export const EntitySchema = z.object({
    entity_id: z.string(),
    kind: z.string(),
    designations: z.optional(z.set(z.string())),
}) satisfies z.ZodType<Entity>;

export const User = z.object({
    user_id: z.uuid(),
    email: z.email(),
});
export type User = z.infer<typeof User>;

export const Reference = z.object({
    reference_id: z.int(),
    pubmed_id: z.int(),
    pmc_id: z.int(),
    pmc_open: z.boolean(),
    doi: z.string(),
    authors: z.string(),
    title: z.string(),
    journal: z.string(),
    volume: z.string(),
    number: z.nullable(z.string()),
    pages: z.string(),
    year: z.int(),
    abstract: z.string().optional(),
    body: z.string().optional(),
});
export type Reference = z.infer<typeof Reference>;

export const Relation = z.object({
    predicate: z.string(),
    subject: z.string(),
    object: z.string(),
});
export type Relation = z.infer<typeof Relation>;

export const AnnotationState = z.object({
    user: User,
    reference: Reference,
    entities: z
        .record(z.string(), EntitySchema)
        .transform((obj) => new Map(Object.entries(obj))),
    pointers: z
        .record(z.string(), Pointer)
        .transform(
            (obj) =>
                new Map(
                    Object.entries(obj).map(
                        ([k, v]) => [Number(k), v] as const,
                    ),
                ),
        ),
    relations: z.array(Relation).transform((arr) => new Set(arr)),
});
export type AnnotationState = z.infer<typeof AnnotationState>;
