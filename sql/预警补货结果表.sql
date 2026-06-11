CREATE TABLE IF NOT EXISTS ads_inventory_alert_result
(
    run_id String COMMENT '运行批次ID，用于追踪一次预警计算任务',
    calc_date Date COMMENT '业务计算日',
    org_code String COMMENT '机构编码',
    org_name Nullable(String) COMMENT '机构名称',
    product_code String COMMENT '商品编码/SKU',
    product_name Nullable(String) COMMENT '商品名称',
    product_category_code Nullable(String) COMMENT '商品类别编码',
    product_category_name Nullable(String) COMMENT '商品类别名称',
    unit Nullable(String) COMMENT '商品单位',

    inventory_qty Decimal(18, 3) COMMENT '当前库存数量',
    available_inventory_qty Decimal(18, 3) COMMENT '可用库存数量，初版等于当前库存数量',
    effective_inventory_qty Decimal(18, 3) COMMENT '有效库存数量，初版等于当前库存数量',

    sales_avg_7 Decimal(18, 4) COMMENT '近7天日均销量',
    sales_avg_15 Decimal(18, 4) COMMENT '近15天日均销量',
    sales_avg_30 Decimal(18, 4) COMMENT '近30天日均销量',
    base_daily_sales Decimal(18, 4) COMMENT '按7/15/30天回退后的基础日销量',
    correction_factor Decimal(18, 4) COMMENT '综合修正因子',
    corrected_daily_demand Decimal(18, 4) COMMENT '修正后日需求',

    coverage_days Nullable(Decimal(18, 2)) COMMENT '库存覆盖天数：可用库存/基础日销量',
    estimated_sale_days Nullable(Decimal(18, 2)) COMMENT '预计销售时长：当前库存/修正后日需求',
    warning_risk_days Nullable(Decimal(18, 2)) COMMENT '预警风险天数，取覆盖天数和预计销售时长的较小值',

    safety_stock_qty Decimal(18, 3) COMMENT '安全库存阈值',
    safety_stock_gap Decimal(18, 3) COMMENT '安全库存缺口：安全库存阈值-有效库存',
    expired_stock_qty Decimal(18, 3) COMMENT '过期库存数量，当前缺少批次效期字段时写0',
    expiring_stock_qty Decimal(18, 3) COMMENT '临期库存数量，当前缺少批次效期字段时写0',
    expiring_stock_ratio Decimal(18, 4) COMMENT '临期库存占比，当前缺少批次效期字段时写0',

    alert_status LowCardinality(String) COMMENT '预警状态，如 warning 或 sufficient',
    alert_type LowCardinality(String) COMMENT '预警类型，如库存预警、临期预警、过期提示、库存充足',
    warning_level Nullable(UInt8) COMMENT '预警等级，3最紧急、2次之、1较轻，库存充足为空',
    warning_level_name Nullable(String) COMMENT '预警等级名称',
    reason String COMMENT '预警触发原因或库存充足说明',
    missing_fields String COMMENT '当前计算缺失的字段清单',

    created_at DateTime DEFAULT now() COMMENT '结果写入时间'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(calc_date)
ORDER BY (calc_date, run_id, org_code, product_code);


CREATE TABLE IF NOT EXISTS ads_replenishment_forecast_result
(
    run_id String COMMENT '运行批次ID，用于追踪一次补货预测任务',
    calc_date Date COMMENT '业务计算日',
    org_code String COMMENT '机构编码',
    org_name Nullable(String) COMMENT '机构名称',
    product_code String COMMENT '商品编码/SKU',
    product_name Nullable(String) COMMENT '商品名称',
    product_category_code Nullable(String) COMMENT '商品类别编码',
    product_category_name Nullable(String) COMMENT '商品类别名称',
    supplier_name Nullable(String) COMMENT '供应商名称',
    unit Nullable(String) COMMENT '商品单位',

    inventory_qty Decimal(18, 3) COMMENT '当前库存数量',
    effective_inventory_qty Decimal(18, 3) COMMENT '有效库存数量，初版等于当前库存数量',
    in_transit_qty Decimal(18, 3) COMMENT '计入补货计算的入库方向在途数量',

    sales_avg_7 Decimal(18, 4) COMMENT '近7天日均销量',
    sales_avg_15 Decimal(18, 4) COMMENT '近15天日均销量',
    sales_avg_30 Decimal(18, 4) COMMENT '近30天日均销量',
    base_daily_sales Decimal(18, 4) COMMENT '按7/15/30天回退后的基础日销量',
    correction_factor Decimal(18, 4) COMMENT '综合修正因子',
    corrected_daily_demand Decimal(18, 4) COMMENT '修正后日需求',

    purchase_cycle_days Decimal(18, 2) COMMENT '进货周期天数，初版来自配置默认值',
    replenish_cycle_demand Decimal(18, 3) COMMENT '补货周期需求：修正后日需求*进货周期',
    safety_stock_mode LowCardinality(String) COMMENT '安全库存计算模式，初版为buffer_days',
    safety_stock_qty Decimal(18, 3) COMMENT '安全库存数量',
    gap_qty Decimal(18, 3) COMMENT '补货缺口：周期需求+安全库存-有效库存-在途库存',

    raw_replenish_qty Decimal(18, 3) COMMENT '原始建议补货数量：max(补货缺口,0)',
    min_order_qty Decimal(18, 3) COMMENT '最小订货量',
    pack_qty Decimal(18, 3) COMMENT '箱规或包装规格',
    system_replenish_qty Decimal(18, 3) COMMENT '系统测算补货数量，按MOQ和箱规取整',
    manual_replenish_qty Nullable(Decimal(18, 3)) COMMENT '人工调整补货数量，初版为空',
    final_replenish_qty Decimal(18, 3) COMMENT '最终建议补货数量，初版等于系统测算数量',

    replenish_after_days Decimal(18, 2) COMMENT '建议补货等待天数',
    suggested_replenish_date Date COMMENT '建议补货日期',
    expected_arrival_date Date COMMENT '预计到货日期',

    stop_replenishment_reason Nullable(String) COMMENT '停止补货原因，初版缺少临期字段时为空',
    missing_fields String COMMENT '当前计算缺失的字段清单',

    created_at DateTime DEFAULT now() COMMENT '结果写入时间'
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(calc_date)
ORDER BY (calc_date, run_id, org_code, product_code);
