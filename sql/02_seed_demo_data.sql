DELETE FROM ads_inventory_forecast;
DELETE FROM ads_inventory_alert;
DELETE FROM fact_inventory_snapshot;
DELETE FROM fact_pos_transaction;
DELETE FROM dim_base_info;

INSERT INTO dim_base_info (
    "所属服务区",
    "机构编码",
    "服务区方向",
    "门店编号",
    "门店名称",
    "摄像机编号",
    "摄像机名称"
)
VALUES
('天营东区服务区', 91001, '上行', 'STORE001', '东区服务区便利店', 'CAM001', '东区便利店摄像机'),
('天营西区服务区', 91002, '下行', 'STORE002', '西区服务区便利店', 'CAM002', '西区便利店摄像机');

INSERT INTO fact_inventory_snapshot (
    "门店编号",
    "商品类别",
    "商品名称",
    "SKU货号",
    "商品品牌",
    "商品规格",
    "库存数量",
    "可用库存",
    "主供应商名称",
    "供应商编号",
    "最小订货数量",
    "仓库",
    "安全阈值",
    "批次效期",
    "商品有效期",
    "进货周期",
    "配送周期",
    "送货天数",
    "安全缓冲天数",
    "动态安全库存",
    "在途数量",
    "基础修正因子K0",
    "修正因子"
)
VALUES
(
    'STORE001',
    '饮料',
    '矿泉水',
    1001001,
    '天营优选',
    550,
    8,
    8,
    '天营饮品供应商',
    20001,
    12,
    '中心仓',
    12,
    EXTRACT(EPOCH FROM CURRENT_DATE + INTERVAL '300 days')::BIGINT,
    365,
    1,
    1,
    0,
    2,
    12,
    0,
    1.00,
    1.10
),
(
    'STORE001',
    '食品',
    '桶装方便面',
    1002001,
    '天营优选',
    120,
    42,
    40,
    '天营食品供应商',
    20002,
    6,
    '中心仓',
    10,
    EXTRACT(EPOCH FROM CURRENT_DATE + INTERVAL '150 days')::BIGINT,
    180,
    2,
    1,
    0,
    2,
    10,
    6,
    1.00,
    1.00
),
(
    'STORE001',
    '短保',
    '短保面包',
    1003001,
    '天营烘焙',
    80,
    12,
    12,
    '天营短保供应商',
    20003,
    10,
    '前置仓',
    8,
    EXTRACT(EPOCH FROM CURRENT_DATE + INTERVAL '1 day')::BIGINT,
    7,
    1,
    0,
    0,
    2,
    8,
    0,
    1.00,
    1.20
),
(
    'STORE002',
    '短保',
    '鲜牛奶',
    1004001,
    '天营乳业',
    250,
    4,
    4,
    '天营短保供应商',
    20003,
    8,
    '前置仓',
    8,
    EXTRACT(EPOCH FROM CURRENT_DATE + INTERVAL '3 days')::BIGINT,
    10,
    1,
    1,
    0,
    2,
    8,
    0,
    1.00,
    1.15
),
(
    'STORE002',
    '饮料',
    '即饮咖啡',
    1005001,
    '天营咖啡',
    300,
    80,
    78,
    '天营饮品供应商',
    20001,
    12,
    '中心仓',
    12,
    EXTRACT(EPOCH FROM CURRENT_DATE + INTERVAL '200 days')::BIGINT,
    270,
    1,
    1,
    0,
    2,
    12,
    12,
    1.00,
    1.05
);

INSERT INTO fact_pos_transaction (
    "订单编号",
    "门店编号",
    "交易金额",
    "交易时间",
    "售卖商品",
    "SKU货号",
    "商品名称",
    "销售数量"
)
SELECT
    'STORE001-ORD-WATER-' || gs::TEXT,
    'STORE001',
    30,
    EXTRACT(EPOCH FROM CURRENT_DATE - (8 - gs) * INTERVAL '1 day' + INTERVAL '10 hours')::BIGINT,
    '矿泉水',
    1001001,
    '矿泉水',
    10
FROM generate_series(1, 7) AS gs;

INSERT INTO fact_pos_transaction (
    "订单编号",
    "门店编号",
    "交易金额",
    "交易时间",
    "售卖商品",
    "SKU货号",
    "商品名称",
    "销售数量"
)
SELECT
    'STORE001-ORD-NOODLE-' || gs::TEXT,
    'STORE001',
    45,
    EXTRACT(EPOCH FROM CURRENT_DATE - (8 - gs) * INTERVAL '1 day' + INTERVAL '12 hours')::BIGINT,
    '桶装方便面',
    1002001,
    '桶装方便面',
    5
FROM generate_series(1, 7) AS gs;

INSERT INTO fact_pos_transaction (
    "订单编号",
    "门店编号",
    "交易金额",
    "交易时间",
    "售卖商品",
    "SKU货号",
    "商品名称",
    "销售数量"
)
SELECT
    'STORE001-ORD-BREAD-' || gs::TEXT,
    'STORE001',
    64,
    EXTRACT(EPOCH FROM CURRENT_DATE - (8 - gs) * INTERVAL '1 day' + INTERVAL '9 hours')::BIGINT,
    '短保面包',
    1003001,
    '短保面包',
    8
FROM generate_series(1, 7) AS gs;

INSERT INTO fact_pos_transaction (
    "订单编号",
    "门店编号",
    "交易金额",
    "交易时间",
    "售卖商品",
    "SKU货号",
    "商品名称",
    "销售数量"
)
SELECT
    'STORE002-ORD-MILK-' || gs::TEXT,
    'STORE002',
    90,
    EXTRACT(EPOCH FROM CURRENT_DATE - (8 - gs) * INTERVAL '1 day' + INTERVAL '11 hours')::BIGINT,
    '鲜牛奶',
    1004001,
    '鲜牛奶',
    9
FROM generate_series(1, 7) AS gs;

INSERT INTO fact_pos_transaction (
    "订单编号",
    "门店编号",
    "交易金额",
    "交易时间",
    "售卖商品",
    "SKU货号",
    "商品名称",
    "销售数量"
)
SELECT
    'STORE002-ORD-COFFEE-' || gs::TEXT,
    'STORE002',
    45,
    EXTRACT(EPOCH FROM CURRENT_DATE - (8 - gs) * INTERVAL '1 day' + INTERVAL '13 hours')::BIGINT,
    '即饮咖啡',
    1005001,
    '即饮咖啡',
    3
FROM generate_series(1, 7) AS gs;
