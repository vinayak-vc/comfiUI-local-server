"""A generic Alembic script template."""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op


revision: str
down_revision: str | None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

