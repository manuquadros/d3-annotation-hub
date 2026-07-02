/**
 * Access data surfaced by `+layout.server.ts` and needed to gate a
 * project-management page.
 */
export interface ProjectAccessData {
    /** Global capability: `can_manage` or superuser. */
    isAdmin: boolean;
    /** Whether the user has the `manager` role in {@link currentProjectId}. */
    isProjectManager: boolean;
    /** Project the layout resolved roles against (path id, unless a
     *  `?project=` override is present). */
    currentProjectId: number | null;
}

/**
 * Whether the user may manage `projectId` (view its users, documents, and
 * ontologies).
 *
 * Mirrors the backend `require_manager`: a global admin, or a manager of *this*
 * project. `isProjectManager` is scoped to `currentProjectId`, so it is only
 * trusted when that matches `projectId` — otherwise a `?project=` override
 * could let a manager of another project through.
 */
export function canManageProject(
    data: ProjectAccessData,
    projectId: number,
): boolean {
    return (
        data.isAdmin ||
        (data.isProjectManager && data.currentProjectId === projectId)
    );
}
