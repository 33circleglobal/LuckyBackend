from apps.trees.models import LuckyCircleTree
from apps.accounts.models import CustomUser

from django.db import transaction, models
from django.db.models import Max


@transaction.atomic
def add_user_to_enroller_tree(user: CustomUser) -> LuckyCircleTree:
    # Guard: never create a duplicate node for the same user.
    if LuckyCircleTree.objects.filter(user=user).exists():
        raise ValueError(
            f"User {user} already has an enroller node — "
            "add_user_to_enroller_tree() must not be called twice."
        )

    # ── Superuser → root ──────────────────────────────────────────────────
    if user.is_superuser:
        if LuckyCircleTree.get_root_nodes().exists():
            raise ValueError(
                "A root node already exists. "
                "Only one root (superuser) is allowed in the enroller tree."
            )
        return LuckyCircleTree.add_root(user=user)

    # ── Regular user → child of their sponsor ─────────────────────────────
    if not user.referred_by:
        raise ValueError(
            f"User {user} has no referred_by set — cannot place in enroller tree."
        )

    try:
        sponsor_node: LuckyCircleTree = LuckyCircleTree.objects.select_for_update().get(
            user=user.referred_by
        )
    except LuckyCircleTree.DoesNotExist:
        raise LuckyCircleTree.DoesNotExist(
            f"Sponsor {user.referred_by} does not have an enroller node yet. "
            "Ensure the sponsor is registered before their referrals."
        )

    return sponsor_node.add_child(user=user)
