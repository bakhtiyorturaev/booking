from apps.core.models import ServiceType


def descendant_service_ids(service_ids, active_only=False, parent_overrides=None):
    """Resolve an arbitrary depth tree with one database query."""
    selected = set(service_ids)
    overrides = parent_overrides or {}
    rows = [(pk, overrides.get(pk, parent), active) for pk, parent, active in ServiceType.objects.values_list("pk", "parent_id", "is_active")]
    changed = True
    while changed:
        changed = False
        for pk, parent_id, active in rows:
            if pk not in selected and parent_id in selected and (active or not active_only):
                selected.add(pk)
                changed = True
    if active_only:
        selected.intersection_update(pk for pk, _, active in rows if active)
    return selected


def root_service(service):
    seen = set()
    while service and service.parent_id and service.pk not in seen:
        seen.add(service.pk)
        service = service.parent
    return service


def ancestor_service_ids(service_ids):
    parents = dict(ServiceType.objects.values_list("pk", "parent_id"))
    selected = set(service_ids)
    pending = list(selected)
    while pending:
        parent = parents.get(pending.pop())
        if parent and parent not in selected:
            selected.add(parent)
            pending.append(parent)
    return selected


def active_service_ids():
    rows = list(ServiceType.objects.values_list("pk", "parent_id", "is_active"))
    visible = {pk for pk, parent, active in rows if active and parent is None}
    changed = True
    while changed:
        changed = False
        for pk, parent, active in rows:
            if active and parent in visible and pk not in visible:
                visible.add(pk)
                changed = True
    return visible
