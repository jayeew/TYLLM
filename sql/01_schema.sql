DROP TABLE IF EXISTS ads_inventory_forecast;
DROP TABLE IF EXISTS ads_inventory_alert;
DROP TABLE IF EXISTS fact_inventory_snapshot;
DROP TABLE IF EXISTS fact_pos_transaction;
DROP TABLE IF EXISTS dim_base_info;

CREATE TABLE dim_base_info (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "所属服务区" TEXT NOT NULL,
    "机构编码" NUMERIC,
    "服务区方向" TEXT,
    "门店编号" TEXT NOT NULL,
    "门店名称" TEXT NOT NULL,
    "摄像机编号" TEXT,
    "摄像机名称" TEXT
);

CREATE INDEX idx_dim_base_info_store_code
ON dim_base_info ("门店编号");

CREATE TABLE fact_pos_transaction (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "订单编号" TEXT NOT NULL,
    "门店编号" TEXT NOT NULL,
    "交易金额" NUMERIC(14, 2) NOT NULL,
    "交易时间" BIGINT NOT NULL,
    "售卖商品" TEXT NOT NULL,
    "SKU货号" NUMERIC NOT NULL,
    "商品名称" TEXT NOT NULL,
    "销售数量" NUMERIC(14, 2) NOT NULL
);

CREATE INDEX idx_fact_pos_store_sku_time
ON fact_pos_transaction ("门店编号", "SKU货号", "交易时间");

CREATE UNIQUE INDEX ux_fact_pos_order_sku
ON fact_pos_transaction ("订单编号", "SKU货号");

-- CREATE TABLE fact_inventory_snapshot (
--     id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
--     "门店编号" TEXT NOT NULL,
--     "商品类别" TEXT NOT NULL,
--     "商品名称" TEXT NOT NULL,
--     "SKU货号" NUMERIC NOT NULL,
--     "商品品牌" TEXT,
--     "商品规格" NUMERIC,
--     "库存数量" NUMERIC(14, 2) NOT NULL,
--     "可用库存" NUMERIC(14, 2) NOT NULL,
--     "主供应商名称" TEXT,
--     "供应商编号" NUMERIC,
--     "最小订货数量" NUMERIC(14, 2) NOT NULL,
--     "仓库" TEXT,
--     "安全阈值" NUMERIC(14, 2),
--     "批次效期" BIGINT,
--     "商品有效期" NUMERIC,
--     "进货周期" NUMERIC,
--     "配送周期" NUMERIC,
--     "送货天数" NUMERIC,
--     "安全缓冲天数" NUMERIC,
--     "动态安全库存" NUMERIC(14, 2),
--     "在途数量" NUMERIC(14, 2),
--     "基础修正因子K0" NUMERIC(8, 4),
--     "修正因子" NUMERIC(8, 4)
-- );

CREATE TABLE fact_inventory_snapshot(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "机构编码" NUMERIC(14, 2) NOT NULL,
    "机构名称" TEXT NOT NULL,
    "商品编码" NUMERIC(10, 0) NOT NULL,
    "国际条码" NUMERIC(13, 0) NOT NULL,
    "商品类别" NUMERIC(6, 0) NOT NULL,
    "商品类别名称" TEXT NOT NULL,
    "供应商" TEXT NOT NULL,
    "单位" TEXT NOT NULL,
    "规格" TEXT,
    "商品名称" TEXT NOT NULL,
    "商品状态" TEXT NOT NULL,
    "库存数量" NUMERIC(14, 2) NOT NULL,
    "零售价" NUMERIC(14, 4) NOT NULL,
    "零售金额" NUMERIC(14, 2) NOT NULL,
    "成本价" NUMERIC(14, 4) NOT NULL,
    "库存金额" NUMERIC(14, 2) NOT NULL,
    "未税成本金额" NUMERIC(14, 2) NOT NULL,
    "毛利率"  NUMERIC(5, 2) NOT NULL,
    "大包装数量" NUMERIC,
    "采购在途数量" NUMERIC(14, 3) NOT NULL,
    "销售在途数量" NUMERIC(14, 3) NOT NULL,
    "要货在途数量" NUMERIC(14, 3) NOT NULL,
    "调拨在途数量" NUMERIC(14, 3) NOT NULL,
    "配送在途数量" NUMERIC(14, 3) NOT NULL,
    "配退在途数量" NUMERIC(14, 3) NOT NULL,
    "最小库存量" NUMERIC(14, 3) NOT NULL,
    "最大库存量" NUMERIC(14, 3) NOT NULL,
    "周转天数" NUMERIC(14, 2) NOT NULL,
    "最后一次销售日期" DATE,
    "最后一次进货日期" DATE
);

CREATE INDEX idx_inventory_store_sku
ON fact_inventory_snapshot ("门店编号", "SKU货号");

CREATE TABLE ads_inventory_alert (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "门店编号" TEXT NOT NULL,
    "SKU货号" NUMERIC NOT NULL,
    "商品名称" TEXT NOT NULL,
    "预警类别" TEXT NOT NULL,
    "预警时间" BIGINT NOT NULL,
    "预警门店" TEXT NOT NULL,
    "预警商品类别" TEXT NOT NULL,
    "预警级别" TEXT NOT NULL,
    "预警详情" TEXT NOT NULL,
    "补货建议" TEXT
);

CREATE INDEX idx_alert_store_sku_level
ON ads_inventory_alert ("门店编号", "SKU货号", "预警级别");

CREATE TABLE ads_inventory_forecast (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "门店编号" TEXT NOT NULL,
    "商品类别" TEXT NOT NULL,
    "商品名称" TEXT NOT NULL,
    "SKU货号" NUMERIC NOT NULL,
    "商品品牌" TEXT,
    "商品规格" NUMERIC,
    "建议补货日期" BIGINT NOT NULL,
    "建议补货数量" NUMERIC(14, 2) NOT NULL,
    "主供应商名称" TEXT,
    "供应商编号" NUMERIC,
    "仓库" TEXT,
    "预计到货时间" BIGINT NOT NULL
);

CREATE INDEX idx_forecast_store_sku
ON ads_inventory_forecast ("门店编号", "SKU货号");

