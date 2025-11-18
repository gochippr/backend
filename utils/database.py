from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def row_to_model(row: tuple, model_class: type[T], column_names: list[str]) -> T:
    """
    Convert a database row tuple to a Pydantic BaseModel instance.

    Args:
        row: Database row tuple
        model_class: Pydantic BaseModel class
        column_names: List of column names in the same order as the row tuple

    Returns:
        Instance of the specified model class
    """
    # Create a dictionary mapping column names to row values
    row_dict = dict(zip(column_names, row))

    # Create and return the model instance
    return model_class(**row_dict)


def row_to_model_with_cursor(row: tuple, model_class: type[T], cursor) -> T:
    """
    Convert a database row tuple to a Pydantic BaseModel instance using cursor description.

    Args:
        row: Database row tuple
        model_class: Pydantic BaseModel class
        cursor: Database cursor with executed query

    Returns:
        Instance of the specified model class
    """
    # Get column names from cursor description
    column_names = [desc[0] for desc in cursor.description]

    return row_to_model(row, model_class, column_names)
