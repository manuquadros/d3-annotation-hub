import { z } from "zod";
import { Map, Set } from "immutable";
import type { AnnotationState } from "$lib/annotation.ts";

export type Pointer = {
    pointer_id: number;
    user_id: string;
    entity_id: string;
    reference_id: number;
    offset: number;
    length: number;
};

export const PointerSchema = z.object({
    pointer_id: z.int(),
    user_id: z.uuid(),
    entity_id: z.string(),
    reference_id: z.int(),
    offset: z.int(),
    length: z.int(),
}) satisfies z.ZodType<Pointer>;

export type Entity = {
    entity_id: string;
    kind: string;
    designations?: Set<string>;
};

export const EntitySchema = z.object({
    entity_id: z.string(),
    kind: z.string(),
    designations: z.optional(z.array(z.string()).transform((arr) => Set(arr))),
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

export type Relation = {
    predicate: string;
    subject: string;
    object: string;
};
export const RelationSchema = z.object({
    predicate: z.string(),
    subject: z.string(),
    object: z.string(),
}) satisfies z.ZodType<Relation>;

export const AnnotationStateSchema = z.object({
    user: UserSchema,
    reference: ReferenceSchema,
    entities: z
        .record(z.string(), EntitySchema)
        .transform((obj) => Map(Object.entries(obj))),
    pointers: z
        .record(z.string(), PointerSchema)
        .transform((obj) =>
            Map(Object.entries(obj).map(([k, v]) => [Number(k), v] as const)),
        ),
    relations: z.array(RelationSchema).transform((arr) => Set(arr)),
});

export interface DropdownState {
    isOpen: boolean;
    position: {
        top: number;
        left: number;
    };
    triggerElement: HTMLElement | null;
}
