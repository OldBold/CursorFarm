import unittest
from systems.campaign import init_campaign_state, update_campaign


class TestCampaignLogic(unittest.TestCase):
    def test_weeks_and_negative_counter_reset(self):
        state = {"dinheiro": 100.0, "campaign": init_campaign_state()}
        new = update_campaign(state, 7)
        self.assertEqual(new.get("weeks_played"), 1)
        self.assertEqual(new.get("weeks_negative_cash_consecutive"), 0)
        self.assertNotEqual(new.get("status"), "LOST")

    def test_negative_no_farms_triggers_loss(self):
        state = {
            "dinheiro": -50.0,
            "fazendas": [],
            "plantacoes_por_fazenda": {},
            "estoque": [],
            "campaign": init_campaign_state(),
        }
        new = update_campaign(state, 28)  # 4 weeks
        self.assertEqual(new.get("weeks_played"), 4)
        self.assertTrue(new.get("weeks_negative_cash_consecutive") >= 4)
        self.assertEqual(new.get("status"), "LOST")
        self.assertIn("sem meios de recuperação", new.get("lost_reason", "").lower())

    def test_crescendo_not_considered_recovery(self):
        # Plantacoes exist but none are PRONTA; should be considered no means of recovery
        state = {
            "dinheiro": -10.0,
            "fazendas": [{"id": 1, "tam": 2}],
            "plantacoes_por_fazenda": {1: [{"estado": "Crescendo", "nome": "Milho"}]},
            "estoque": [],
            "campaign": init_campaign_state(),
        }
        new = update_campaign(state, 7)
        # since money negative and no pronta/estoque, campaign should be lost by the second rule
        self.assertEqual(new.get("status"), "LOST")
        self.assertIn("sem recursos", new.get("lost_reason", "").lower() + new.get("lost_reason", "").lower())

    def test_pronta_prevents_immediate_loss(self):
        state = {
            "dinheiro": -5.0,
            "fazendas": [{"id": 1, "tam": 2}],
            "plantacoes_por_fazenda": {1: [{"estado": "PRONTA", "nome": "Milho"}]},
            "estoque": [],
            "campaign": init_campaign_state(),
        }
        new = update_campaign(state, 7)
        # should not be immediately lost because there is a pronta plant
        self.assertNotEqual(new.get("status"), "LOST")


if __name__ == "__main__":
    unittest.main()
