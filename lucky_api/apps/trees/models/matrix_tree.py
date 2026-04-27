from django.db import models, transaction
from django.db.models import Max

from treebeard.mp_tree import MP_Node

from apps.accounts.models import CustomUser


class LuckyMatrixTree(MP_Node):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matrix_nodes",
    )
    user_left = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="as_left_child",
    )
    user_right = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="as_right_child",
    )

    steplen = 4

    node_order_by = []

    def __str__(self):
        return self.user.username if self.user else f"Empty (path={self.path})"

    @property
    def left_slot_free(self) -> bool:
        return self.user_left_id is None

    @property
    def right_slot_free(self) -> bool:
        return self.user_right_id is None

    class Meta:
        verbose_name = "MLM Binary Node"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["user_left", "user_right"]),
            models.Index(fields=["depth"]),
        ]
