import enum
from sqlalchemy.types import TypeDecorator
from sqlalchemy import Enum as SQLEnum

class CaseInsensitiveEnum(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that wraps SQLEnum.
    It allows case-insensitive string inputs, schema-defined enum inputs, 
    and handles conversion to database-supported uppercase enums on write,
    and returns python enum members on read.
    """
    impl = SQLEnum
    cache_ok = True

    def __init__(self, enum_class, **kwargs):
        super().__init__(enum_class, **kwargs)
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        
        # If it's a python enum member (even from a different Enum class with same values)
        if isinstance(value, enum.Enum):
            # Check if name exists in our target enum_class (matching by name)
            name_upper = value.name.upper()
            if name_upper in self.enum_class.__members__:
                return name_upper
            # Or try matching by value
            val_str = str(value.value).upper()
            for member in self.enum_class:
                if member.value.upper() == val_str:
                    return member.name.upper()
            return name_upper

        # If it is a string
        val_str = str(value).upper()
        if val_str in self.enum_class.__members__:
            return val_str
        
        # Check if any member value matches case-insensitively
        for member in self.enum_class:
            if member.value.upper() == val_str:
                return member.name.upper()

        return val_str

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        
        if isinstance(value, str):
            val_upper = value.upper()
            # Try to look up by member name
            if val_upper in self.enum_class.__members__:
                return self.enum_class[val_upper]
            # Try to look up by member value
            for member in self.enum_class:
                if member.value.upper() == val_upper:
                    return member
        elif isinstance(value, self.enum_class):
            return value

        return value
