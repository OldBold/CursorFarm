import unittest
from systems.achievements import check_weekly_achievements, ACHIEVEMENTS_CATALOG


class TestAchievements(unittest.TestCase):
    def test_first_fazenda_and_hectares(self):
        state = {"fazendas": [{"id": 1, "tam": 3}, {"id": 2, "tam": 2}], "meus_equipamentos": [], "estoque": [], "campaign": {}}
        new = check_weekly_achievements(state)
        self.assertIn("first_fazenda", new)
        self.assertIn("five_hectares", new)

    def test_first_equip_and_harvest(self):
        state = {"fazendas": [], "meus_equipamentos": [{"id": 1}], "estoque": [{"quantidade_kg": 100}], "campaign": {}}
        new = check_weekly_achievements(state)
        self.assertIn("first_equip", new)
        self.assertIn("first_harvest", new)

    def test_net_worth_x2_requires_initial(self):
        # if no initial net worth set, cannot unlock net_worth_x2
        state = {"dinheiro": 1000.0, "campaign": {}}
        new = check_weekly_achievements(state)
        self.assertNotIn("net_worth_x2", new)


if __name__ == "__main__":
    unittest.main()
