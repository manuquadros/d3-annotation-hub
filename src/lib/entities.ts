export type Entity = {
    entity_id: string;
    kind: string;
    designations?: Set<string>;
};

function newEntityID(): string {
    return `entity_${Date.now()}_${Math.random().toString(36).substring(7)}`;
}

export function newEntity(label: string, id: string | null): Entity {
    return {
        entity_id: id ? id : newEntityID(),
        kind: label,
    };
}
