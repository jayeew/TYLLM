from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import unittest

from app.core.alert_rule import build_alert_result
from app.core.forecast_rule import build_forecast_result
from app.core.indicator_calculator import build_inventory_indicators


def make_settings(**overrides):
    values = {
        "alert_factor_k0_phase2": Decimal("1"),
        "alert_factor_k1_workday": Decimal("1"),
        "alert_factor_k1_weekend": Decimal("1"),
        "alert_factor_k2_stable": Decimal("1"),
        "alert_default_safety_stock_qty": Decimal("0"),
        "alert_expiring_stock_ratio_limit": Decimal("0.5"),
        "alert_level1_coverage_days": Decimal("14"),
        "alert_level2_coverage_days": Decimal("7"),
        "alert_level3_coverage_days": Decimal("3"),
        "replenish_default_purchase_cycle_days": Decimal("3"),
        "replenish_safety_buffer_days": Decimal("2"),
        "replenish_default_min_order_qty": Decimal("1"),
        "replenish_default_pack_qty": Decimal("1"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_record(**overrides):
    values = {
        "org_code": "10001",
        "org_name": "测试门店",
        "product_code": "SKU001",
        "product_name": "测试商品",
        "product_category_code": "C01",
        "product_category_name": "测试品类",
        "supplier_name": "测试供应商",
        "unit": "个",
        "inventory_qty": Decimal("10"),
        "large_package_qty": Decimal("1"),
        "purchase_factor": Decimal("1"),
        "purchase_in_transit_qty": Decimal("0"),
        "requisition_in_transit_qty": Decimal("0"),
        "distribution_in_transit_qty": Decimal("0"),
        "min_inventory_qty": Decimal("0"),
        "sales_avg_7": Decimal("1"),
        "sales_avg_15": Decimal("1"),
        "sales_avg_30": Decimal("1"),
    }
    values.update(overrides)
    return values


class CoreRuleTests(unittest.TestCase):
    def test_base_daily_sales_falls_back_to_15_days(self):
        result = build_inventory_indicators(
            record=make_record(
                sales_avg_7=Decimal("0"),
                sales_avg_15=Decimal("2"),
                sales_avg_30=Decimal("5"),
            ),
            settings=make_settings(),
            calc_date=date(2026, 6, 10),
        )

        self.assertEqual(result["base_daily_sales"], Decimal("2.0000"))
        self.assertEqual(result["corrected_daily_demand"], Decimal("2.0000"))

    def test_zero_sales_sets_daily_demand_to_one(self):
        result = build_inventory_indicators(
            record=make_record(
                inventory_qty=Decimal("10"),
                sales_avg_7=Decimal("0"),
                sales_avg_15=Decimal("0"),
                sales_avg_30=Decimal("0"),
            ),
            settings=make_settings(),
            calc_date=date(2026, 6, 10),
        )

        self.assertEqual(result["base_daily_sales"], Decimal("0.0000"))
        self.assertEqual(result["corrected_daily_demand"], Decimal("1.0000"))
        self.assertIsNone(result["coverage_days"])
        self.assertEqual(result["estimated_sale_days"], Decimal("10.00"))

    def test_alert_levels_and_sufficient_status(self):
        cases = [
            (Decimal("2"), 3, "三级预警"),
            (Decimal("5"), 2, "二级预警"),
            (Decimal("10"), 1, "一级预警"),
            (Decimal("20"), None, None),
        ]

        for inventory_qty, level, level_name in cases:
            with self.subTest(inventory_qty=inventory_qty):
                result = build_alert_result(
                    record=make_record(inventory_qty=inventory_qty),
                    settings=make_settings(),
                    calc_date=date(2026, 6, 10),
                    run_id="run-1",
                )
                self.assertEqual(result["warning_level"], level)
                self.assertEqual(result["warning_level_name"], level_name)

    def test_alert_safety_stock_gap_triggers_level_three(self):
        result = build_alert_result(
            record=make_record(inventory_qty=Decimal("20"), min_inventory_qty=Decimal("30")),
            settings=make_settings(),
            calc_date=date(2026, 6, 10),
            run_id="run-1",
        )

        self.assertEqual(result["warning_level"], 3)
        self.assertIn("damaged_qty", result["missing_fields"])

    def test_forecast_rounds_up_by_moq_and_pack(self):
        result = build_forecast_result(
            record=make_record(
                inventory_qty=Decimal("0"),
                sales_avg_7=Decimal("10"),
                large_package_qty=Decimal("24"),
                purchase_factor=Decimal("0"),
            ),
            settings=make_settings(replenish_default_min_order_qty=Decimal("60")),
            calc_date=date(2026, 6, 10),
            run_id="run-1",
        )

        self.assertEqual(result["gap_qty"], Decimal("50.000"))
        self.assertEqual(result["system_replenish_qty"], Decimal("72.000"))
        self.assertEqual(result["final_replenish_qty"], Decimal("72.000"))
        self.assertIn("purchase_order_history", result["missing_fields"])

    def test_forecast_negative_gap_generates_zero_replenishment(self):
        result = build_forecast_result(
            record=make_record(inventory_qty=Decimal("100"), sales_avg_7=Decimal("1")),
            settings=make_settings(),
            calc_date=date(2026, 6, 10),
            run_id="run-1",
        )

        self.assertEqual(result["gap_qty"], Decimal("-95.000"))
        self.assertEqual(result["raw_replenish_qty"], Decimal("0.000"))
        self.assertEqual(result["system_replenish_qty"], Decimal("0.000"))


if __name__ == "__main__":
    unittest.main()
