import unittest
import inspect

from data import catalogs


class TestCatalogsSchema(unittest.TestCase):
    def test_culturas_catalogo_schema(self):
        self.assertTrue(hasattr(catalogs, 'CULTURAS_CATALOGO'))
        cults = catalogs.CULTURAS_CATALOGO
        self.assertIsInstance(cults, list)
        required = {"nome", "preco_venda", "kg_hectare", "dias_totais", "solo_ideal", "nivel_req", "custo_semente", "tipo_armazenagem", "tipo_cultura"}
        for c in cults:
            self.assertIsInstance(c, dict)
            self.assertTrue(required.issubset(set(c.keys())))
            self.assertIsInstance(c['nome'], str)
            self.assertIsInstance(c['preco_venda'], (int, float))
            self.assertIsInstance(c['kg_hectare'], (int, float))
            self.assertIsInstance(c['dias_totais'], int)
            self.assertIn(c['tipo_armazenagem'], ("Silo", "Armazém"))
            # regra: Cereais/Leguminosas -> Silo
            if c.get('tipo_cultura') in ["Cereais", "Leguminosas"]:
                self.assertEqual(c['tipo_armazenagem'], "Silo")
            else:
                self.assertIn(c['tipo_armazenagem'], ("Silo", "Armazém"))

    def test_maquinas_catalogo_schema(self):
        self.assertTrue(hasattr(catalogs, 'MAQUINAS_CATALOGO'))
        maqs = catalogs.MAQUINAS_CATALOGO
        self.assertIsInstance(maqs, list)
        required = {"nome", "funcao", "preco", "manutencao", "nivel_req", "nome_base", "valor_bonus", "capacidade"}
        for m in maqs:
            self.assertIsInstance(m, dict)
            self.assertTrue(required.issubset(set(m.keys())))
            self.assertIsInstance(m['nome'], str)
            self.assertIsInstance(m['preco'], (int, float))
            self.assertIsInstance(m['manutencao'], (int, float))
            self.assertIsInstance(m['nivel_req'], int)
            self.assertIsInstance(m['valor_bonus'], (int, float))
            self.assertIsInstance(m['capacidade'], int)
            if m['funcao'] == 'Armazenagem':
                self.assertEqual(m['valor_bonus'], 0)
                self.assertGreater(m['capacidade'], 0)
            else:
                self.assertGreaterEqual(m['valor_bonus'], 0)
                self.assertEqual(m['capacidade'], 0)

    def test_shared_constants(self):
        self.assertTrue(hasattr(catalogs, 'TIPOS_DE_SOLO'))
        self.assertTrue(isinstance(catalogs.TIPOS_DE_SOLO, list))
        self.assertTrue(hasattr(catalogs, 'OPCOES_BASE_FAZENDA'))
        self.assertTrue(isinstance(catalogs.OPCOES_BASE_FAZENDA, list))
        self.assertTrue(hasattr(catalogs, 'SALARIOS_GERENTE'))
        self.assertTrue(isinstance(catalogs.SALARIOS_GERENTE, dict))


if __name__ == '__main__':
    unittest.main()
