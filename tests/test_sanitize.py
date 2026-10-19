
import unittest

from sanitize import sanitize_sensor_values


class TestSanitizeSensorValues(unittest.TestCase):

    def test_mixed_values_and_clipping(self):
        values = ["12.5", 20, None, "invalid", -4, 501, 500, 0]

        result = sanitize_sensor_values(values)

        self.assertEqual(result, [12.5, 20.0, 500.0, 500.0, 0.0])

    def test_empty_and_entirely_invalid_inputs(self):
        self.assertEqual(sanitize_sensor_values([]), [])
        self.assertEqual(
            sanitize_sensor_values([None, "invalid", -5]),
            [],
        )

    def test_numeric_conversion_and_non_finite_values(self):
        values = ["25", 42.5, float("nan"), float("inf")]

        result = sanitize_sensor_values(values)

        self.assertEqual(result, [25.0, 42.5])


if __name__ == "__main__":
    unittest.main()
