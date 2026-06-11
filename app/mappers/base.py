class ClickHouseMapper:
    """ClickHouse 表/视图字段映射基类。"""

    __tablename__: str
    alias: str
    columns: dict[str, str]

    @classmethod
    def field(cls, field_name: str, alias: str | None = None) -> str:
        """把代码字段名转成 SQL 字段表达式。"""
        try:
            column_name = cls.columns[field_name]
        except KeyError as exc:
            raise KeyError(
                f"没有为字段 {field_name} 配置 {cls.__tablename__} 列名"
            ) from exc
        return f"{alias or cls.alias}.{column_name}"

    @classmethod
    def select_clause(cls, alias: str | None = None) -> str:
        """生成 SELECT 字段列表，并把结果列名统一成代码字段名。"""
        return ", ".join(
            f"{cls.field(field_name, alias=alias)} AS {field_name}"
            for field_name in cls.columns
        )
