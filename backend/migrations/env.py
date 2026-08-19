from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata

_TYPE_BOUND_ENUM_CHECKS = {
    "listing_status",
    "market_status",
    "snapshot_market_status",
    "listing_event_type",
    "duplicate_review_status",
    "collection_run_status",
    "raw_listing_status",
    "due_diligence_access_method",
    "confidential_data_status",
    "financial_metric_type",
    "financial_verification_status",
    "due_diligence_event_type",
    "source_market_status",
}


def include_object(object_, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    # SQLAlchemy's non-native Enum emits these checks from type metadata. Alembic's
    # PostgreSQL check-constraint comparator otherwise reports them as removals.
    if type_ == "check_constraint" and name in _TYPE_BOUND_ENUM_CHECKS:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
