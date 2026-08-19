import uuid

from sqlalchemy.orm import Session

from app.models.tracking import DuplicateReviewStatus, PossibleDuplicate
from app.repositories import tracking as repository
from app.schemas.tracking import DuplicateResolutionAction
from app.services.tracking import resolve_possible_duplicate


def find_possible_duplicates(
    db: Session,
    *,
    status: DuplicateReviewStatus | None,
    offset: int,
    limit: int,
) -> list[PossibleDuplicate]:
    return repository.list_possible_duplicates(
        db, status=status, offset=offset, limit=limit
    )


def resolve_review(
    db: Session, review_id: uuid.UUID, action: DuplicateResolutionAction
) -> PossibleDuplicate | None:
    review = repository.get_possible_duplicate(db, review_id)
    if review is None:
        return None
    return resolve_possible_duplicate(db, review, action)
