from apps.trees.models import LuckyMatrixTree
from apps.accounts.models import CustomUser

from django.db import transaction, models
from django.db.models import Max


def _attach_child(
    parent_node: LuckyMatrixTree, side: str, user: CustomUser
) -> LuckyMatrixTree:
    new_node: LuckyMatrixTree = parent_node.add_child(user=user)

    if side == "left":
        parent_node.user_left = new_node
        parent_node.save(update_fields=["user_left"])
    else:
        parent_node.user_right = new_node
        parent_node.save(update_fields=["user_right"])

    return new_node


@transaction.atomic
def add_user_to_matrix_tree(user: CustomUser) -> LuckyMatrixTree:
    # ── 1. Empty tree → first user becomes root ───────────────────────────
    if not LuckyMatrixTree.get_root_nodes().exists():
        return LuckyMatrixTree.add_root(user=user)

    # ── 2/3. Try sponsor's own slots first ───────────────────────────────
    sponsor: LuckyMatrixTree = LuckyMatrixTree.objects.select_for_update().get(
        user=user.referred_by
    )
    sponsor.refresh_from_db()

    if sponsor.left_slot_free:
        return _attach_child(sponsor, side="left", user=user)

    if sponsor.right_slot_free:
        return _attach_child(sponsor, side="right", user=user)

    sponsor_depth: int = sponsor.depth
    max_depth: int = (
        LuckyMatrixTree.objects.filter(
            path__startswith=sponsor.path
        ).aggregate(  # sponsor + all descendants
            Max("depth")
        )[
            "depth__max"
        ]
    ) or sponsor_depth

    for depth in range(sponsor_depth + 1, max_depth + 2):  # +2 to allow one new level
        if depth > 20:
            raise ValueError(
                f"Sponsor subtree is full: depth-20 limit reached under sponsor id={sponsor.pk}."
            )
        candidates = (
            sponsor.get_descendants()
            .filter(depth=depth)
            .filter(
                models.Q(user_left__isnull=True) | models.Q(user_right__isnull=True)
            )
            .select_for_update()
            .order_by("path")
        )
        for candidate in candidates:

            candidate.refresh_from_db()

            if candidate.left_slot_free:
                return _attach_child(candidate, side="left", user=user)

            if candidate.right_slot_free:
                return _attach_child(candidate, side="right", user=user)

    raise RuntimeError(
        "add_user_to_matrix_tree: no free slot found in sponsor subtree — unexpected state."
    )
