import unittest
from systems.stats import init_campaign_stats, record_revenue, record_costs, record_harvested, record_sold, week_finalize


class TestCampaignStats(unittest.TestCase):
    def test_basic_financials_and_week_finalize(self):
        state = {"dinheiro": 100.0}
        # initialize and record
        record_costs(state, 20.0)
        record_revenue(state, 50.0)
        # totals should be applied only after week_finalize
        self.assertEqual(state["campaign_stats"]["total_costs"], 0.0)
        self.assertEqual(state["campaign_stats"]["total_revenue"], 0.0)
        self.assertEqual(state["campaign_stats"]["net_profit"], 0.0)
        # finalize week: dinheiro is 100 => positive
        week_finalize(state)
        self.assertEqual(state["campaign_stats"]["weeks_positive_cash"], 1)
        self.assertEqual(state["campaign_stats"]["total_costs"], 20.0)
        self.assertEqual(state["campaign_stats"]["total_revenue"], 50.0)
        self.assertEqual(state["campaign_stats"]["net_profit"], 30.0)

    def test_harvest_and_sold_tracking(self):
        state = {"dinheiro": 0}
        record_harvested(state, "Milho", 200)
        record_sold(state, "Milho", 200, 400.0)
        self.assertEqual(state["campaign_stats"]["total_harvested_by_culture"]["Milho"], 200)
        self.assertEqual(state["campaign_stats"]["total_sold_by_culture"]["Milho"], 200)
        # revenue is applied at week_finalize
        week_finalize(state)
        self.assertEqual(state["campaign_stats"]["total_revenue"], 400.0)


if __name__ == "__main__":
    unittest.main()
