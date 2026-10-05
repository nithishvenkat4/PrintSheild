from datetime import timezone
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import TypeDecorator, String, JSON, DateTime
from geoalchemy2 import Geography

Base = declarative_base()


class UTCDatetime(TypeDecorator):
    """
    Timezone-aware DateTime. Automatically ensures loaded datetimes are timezone-aware (UTC).
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class PointGeography(TypeDecorator):
    """
    Custom type decorator for PostGIS GEOGRAPHY(Point, 4326).
    Compiles to PostGIS Geography on PostgreSQL and String on SQLite (for portable testing).
    """
    impl = Geography(geometry_type="POINT", srid=4326)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect is None:
            return self.impl
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(255))
        return dialect.type_descriptor(Geography(geometry_type="POINT", srid=4326))


class IPAddressType(TypeDecorator):
    """
    Custom type decorator for IP addresses.
    Compiles to PostgreSQL INET and String(45) on SQLite.
    """
    impl = String(45)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect is not None and dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import INET
            return dialect.type_descriptor(INET)
        return dialect.type_descriptor(String(45))


class JSONBType(TypeDecorator):
    """
    Custom type decorator for JSONB.
    Compiles to PostgreSQL JSONB and generic JSON on other dialects.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect is not None and dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)
