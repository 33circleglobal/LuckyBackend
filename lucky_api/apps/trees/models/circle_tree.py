from django.db import models, transaction
from django.db.models import Max

from treebeard.mp_tree import MP_Node

from apps.accounts.models import CustomUser


class LuckyCircleTree(MP_Node):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enroller_node",
    )

    steplen = 4

    node_order_by = []

    def __str__(self):
        return self.user.username if self.user else f"Empty (path={self.path})"

    class Meta:
        verbose_name = "Enroller Tree Node"
        indexes = [
            models.Index(fields=["user"]),
        ]
