from typing import Type, TypeVar

from related import to_model, to_dict


ModelType = TypeVar('ModelType')


class Model:
    @classmethod
    def from_dict(cls: Type[ModelType], data: dict = None, **kwargs) -> ModelType:
        """Factory that allows to pass extra kwargs without errors."""
        data = data.copy() if data else {}
        data.update(kwargs)
        return to_model(cls, data)

    def to_dict(self, **kwargs) -> dict:
        return to_dict(self, **kwargs)
