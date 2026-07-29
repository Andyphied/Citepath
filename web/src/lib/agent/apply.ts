/**
 * Whether an in-flight agent response should update UI state.
 * Discard when the active workspace changed mid-request.
 */
export function shouldApplyAgentResponse(
  requestWorkspaceId: string,
  activeWorkspaceId: string | null | undefined,
): boolean {
  return Boolean(
    activeWorkspaceId && activeWorkspaceId === requestWorkspaceId,
  );
}
