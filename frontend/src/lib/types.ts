import { z } from "zod";
import { Map, Set, Record } from "immutable";
import type { Map as ImmutableMap } from "immutable";


export type Pointer = {
    entity_id: string;
    reference_id: number;
    offset: number;
    length: number;
};

export const PointerSchema = z.object({
    entity_id: z.string(),
    reference_id: z.int(),
    offset: z.int(),
    length: z.int(),
}) satisfies z.ZodType<Pointer>;

export type Entity = {
    entity_id: string;
    uri?: string | null;
    preferred_name: string;
    kind: string;
    synonyms: Set<string>;
    confirmed: boolean;
};

export const EntitySchema = z.object({
    entity_id: z.string(),
    uri: z.string().nullish(),
    preferred_name: z.string(),
    kind: z.string(),
    synonyms: z.array(z.string()).transform((arr) => Set(arr)),
    confirmed: z.boolean().default(true),
}) satisfies z.ZodType<Entity>;

export type User = {
    user_id: string;
    email: string;
};
export const UserSchema = z.object({
    user_id: z.uuid(),
    email: z.email(),
}) satisfies z.ZodType<User>;

export type Reference = {
    reference_id: number;
    pubmed_id: number;
    pmc_id: number;
    pmc_open: boolean;
    doi: string;
    authors: string;
    title: string;
    journal: string;
    volume: string;
    number: string | null;
    pages: string;
    year: number;
    abstract?: string;
    body?: string;
};
export const ReferenceSchema = z.object({
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
}) satisfies z.ZodType<Reference>;

// Create an Immutable Record for Relation to ensure value-based equality
/** @internal */
const RelationRecordFactory = Record({
    relation_id: null as number | null,
    predicate: "",
    subject: "",
    object: "",
});

export type Relation = ReturnType<typeof RelationRecordFactory>;

// Helper to create a Relation from plain object
export function createRelation(obj: {
    relation_id?: number | null;
    predicate: string;
    subject: string;
    object: string;
}): Relation {
    return RelationRecordFactory(obj);
}

export const RelationSchema = z
    .object({
        relation_id: z.number().int().nullable().optional(),
        predicate: z.string(),
        subject: z.string(),
        object: z.string(),
    })
    .transform((obj) => createRelation(obj));

export type EntitySearchResult = {
    entity_id: string;
    preferred_name: string;
    kind: string;
    uri?: string;
    confirmed: boolean;
};

export type EditorState =
    | { mode: "closed" }
    | { mode: "create"; offset: number; length: number; sentenceStart: number }
    | { mode: "edit-pointer"; pointerId: string; sentenceStart: number }
    | { mode: "edit-entity"; entityId: string };

export const AnnotationStateSchema = z.object({
    user: UserSchema,
    reference: ReferenceSchema,
    project_id: z.int(),
    entities: z
        .array(EntitySchema)
        .default([])
        .transform((arr) => Map(arr.map((e) => [e.entity_id, e] as const))),
    pointers: z
        .array(PointerSchema)
        .transform(
            (arr): ImmutableMap<string, Pointer> =>
                Map(
                    arr.map((p, i) => [`ptr_${i}`, p] as const),
                ) as ImmutableMap<string, Pointer>,
        ),
    relations: z.array(RelationSchema).transform((arr) => Set(arr)),
    completed: z.boolean().default(false),
});
