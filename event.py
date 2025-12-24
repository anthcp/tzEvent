import pendulum
import datetime as _dt
from datetime import datetime as py_datetime

class Event(pendulum.DateTime):
    _forced_tz = "UTC"

    def __new__(cls, year, month, day,
            hour=0, minute=0, second=0, microsecond=0,
            tzinfo=None, **kwargs):
        
        is_internal = kwargs.pop("_internal_call", False)
        # Allow:
        # 1) our own factories (_internal_call)
        # 2) Pendulum internal cloning (tzinfo is already set)
        if not is_internal and tzinfo is None:
            raise TypeError(
                f"Direct instantiation disabled. "
                f"Use {cls.__name__}.datetime()/from_datetime()/now()."
            )
        return super().__new__(
            cls,
            year, month, day,
            hour, minute, second, microsecond,
            tzinfo=tzinfo
        )

    @classmethod
    def create_context(cls, timezone_name: str):
        valid_tz = pendulum.timezone(timezone_name).name
        return type(f"Event_{valid_tz.replace('/', '_')}", (cls,), {"_forced_tz": valid_tz})

    # ---------- Canonical constructors (always normalize to _forced_tz) ----------

    @classmethod
    def datetime(cls, year, month, day, hour=0, minute=0, second=0, microsecond=0):
        # Treat these fields as "wall clock" in the forced tz
        p_obj = pendulum.datetime(year, month, day, hour, minute, second, microsecond, tz=cls._forced_tz)
        return cls.from_any_datetime(p_obj)

    @classmethod
    def now(cls):
        return cls.from_any_datetime(pendulum.now(cls._forced_tz))

    @classmethod
    def from_datetime(cls, dt: py_datetime, *, assume_tz: str | None = None):
        """
        Accept stdlib datetime (naive or aware):
        - if naive: assume_tz if provided else forced_tz
        - if aware: respect its tz
        then normalize to forced_tz
        """
        if not isinstance(dt, py_datetime):
            raise TypeError("from_datetime expects a stdlib datetime.datetime")

        if dt.tzinfo is None:
            src_tz = assume_tz or cls._forced_tz
            p_obj = pendulum.datetime(
                dt.year, dt.month, dt.day,
                dt.hour, dt.minute, dt.second, dt.microsecond,
                tz=src_tz
            )
        else:
            # pendulum.instance keeps the existing tzinfo
            p_obj = pendulum.instance(dt)

        return cls.from_any_datetime(p_obj)

    @classmethod
    def from_isoformat(cls, s: str, *, assume_tz: str | None = None):
        """
        Parse ISO string. If it has no offset/tz, assume assume_tz or forced_tz.
        """
        p = pendulum.parse(s, strict=False)
        if p.tzinfo is None:
            p = p.replace(tzinfo=pendulum.timezone(assume_tz or cls._forced_tz))
        return cls.from_any_datetime(p)

    # ---------- Semantics helpers ----------

    def is_same_moment(self, other) -> bool:
        """
        True if same absolute instant (including microseconds).
        """
        if isinstance(other, py_datetime):
            other_p = pendulum.instance(other) if other.tzinfo else pendulum.datetime(
                other.year, other.month, other.day,
                other.hour, other.minute, other.second, other.microsecond,
                tz=self._forced_tz
            )
        elif isinstance(other, pendulum.DateTime):
            other_p = other
        else:
            return False

        # Equality on aware datetimes compares the instant (not the display tz)
        return self.in_timezone("UTC") == other_p.in_timezone("UTC")

    def convert(self, target_event_class):
        """
        Rebind this instant into another Event context class (normalize to its forced tz).
        """
        return target_event_class.from_any_datetime(self.in_timezone(target_event_class._forced_tz))

    @classmethod
    def date_at(cls, year, month, day):
        """
        Create an Event at midnight in the event's forced timezone.
        """
        p_obj = pendulum.datetime(year, month, day, 0, 0, 0, tz=cls._forced_tz)
        return cls.from_any_datetime(p_obj)
    
    @classmethod
    def from_any_datetime(cls, obj):
        # stdlib datetime -> pendulum
        if isinstance(obj, _dt.datetime) and not isinstance(obj, pendulum.DateTime):
            obj = pendulum.instance(obj)

        # naive -> assume forced tz
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=pendulum.timezone(cls._forced_tz))

        # normalize to forced tz
        obj = obj.in_timezone(cls._forced_tz)

        return cls(
            obj.year, obj.month, obj.day,
            obj.hour, obj.minute, obj.second,
            obj.microsecond,
            tzinfo=obj.tzinfo,
            _internal_call=True
        )
