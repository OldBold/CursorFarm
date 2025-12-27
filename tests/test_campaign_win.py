import unittest
from systems.campaign import init_campaign_state, update_campaign, WIN_NET_WORTH_MULTIPLIER, WIN_WEEKS_POSITIVE_CASH


class TestCampaignWin(unittest.TestCase):
    def test_baseline_fallback_set(self):
        # initial_net_worth should be set when missing and weeks_played == 0
        state = {"dinheiro": 100.0, "fazendas": [], "meus_equipamentos": [], "estoque": [], "campaign": init_campaign_state()}
        camp = update_campaign(state, 7)
        self.assertIn("initial_net_worth", camp)
        self.assertGreaterEqual(camp.get("initial_net_worth"), 0)

    def test_win_condition_triggers(self):
        # Set initial baseline and craft state that exceeds multiplier and has enough positive weeks
        initial = 100.0
        campaign = init_campaign_state()
        campaign["initial_net_worth"] = initial
        campaign["weeks_positive_cash_consecutive"] = WIN_WEEKS_POSITIVE_CASH

        # create state with high net worth via dinheiro and assets
        state = {
            "dinheiro": 0.0,
            "fazendas": [{"preco": 0}],
            "meus_equipamentos": [{"preco": 0}],
            "estoque": [],
            "campaign": campaign,
        }
        # boost dinheiro so compute_net_worth >= initial * multiplier
        state["dinheiro"] = initial * WIN_NET_WORTH_MULTIPLIER + 10.0

        new = update_campaign(state, 7)
        self.assertEqual(new.get("status"), "WON")
        self.assertIn("won_reason", new)


if __name__ == "__main__":
    unittest.main()
